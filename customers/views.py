from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Case, Count, IntegerField, Max, Q, Value, When
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ActivityForm, CustomerForm, SignUpForm
from .models import Activity, Customer

PAGE_SIZE = 20
SEARCH_FIELDS = ("first_name", "last_name", "company", "email", "phone", "city")

# Pipeline order, used to sort by status in a meaningful way.
STATUS_ORDER = Case(
    *[When(status=value, then=Value(i)) for i, (value, _) in enumerate(Customer.Status.choices)],
    output_field=IntegerField(),
)

# Sortable columns on the list view: URL key -> (label, ORDER BY fields)
SORT_COLUMNS = {
    "name": ("Name", ("last_name", "first_name")),
    "company": ("Company", ("company", "last_name")),
    "status": ("Status", ("status_order", "last_name")),
    "owner": ("Owner", ("owner__first_name", "owner__username", "last_name")),
    "activity": ("Last activity", ("last_activity", "last_name")),
    "created": ("Created", ("created_at",)),
}


def register(request):
    if request.user.is_authenticated:
        return redirect("customers:home")

    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Welcome, {user.first_name}! Your account is ready.")
        return redirect("customers:home")

    return render(request, "registration/register.html", {"form": form})


@login_required
def home(request):
    counts = {
        row["status"]: row["n"]
        for row in Customer.objects.order_by().values("status").annotate(n=Count("id"))
    }
    total = sum(counts.values())
    pipeline = [
        {
            "value": value,
            "label": label,
            "count": counts.get(value, 0),
            "percent": round(counts.get(value, 0) * 100 / total, 1) if total else 0,
        }
        for value, label in Customer.Status.choices
    ]

    my_open = (
        Customer.objects.filter(owner=request.user, status__in=Customer.OPEN_STATUSES)
        .annotate(last_activity=Max("activities__created_at"), status_order=STATUS_ORDER)
        .order_by("status_order", "last_name")[:8]
    )

    context = {
        "total": total,
        "pipeline": pipeline,
        "my_open": my_open,
        "my_open_count": Customer.objects.filter(
            owner=request.user, status__in=Customer.OPEN_STATUSES
        ).count(),
        "recent_activity": Activity.objects.select_related("customer", "created_by")[:8],
        "recent_customers": Customer.objects.order_by("-created_at")[:5],
    }
    return render(request, "customers/home.html", context)


@login_required
def customer_list(request):
    query = request.GET.get("q", "").strip()
    view = request.GET.get("view", "all")
    status = request.GET.get("status", "")
    sort = request.GET.get("sort", "name")

    customers = Customer.objects.select_related("owner").annotate(
        last_activity=Max("activities__created_at"),
        status_order=STATUS_ORDER,
    )

    if view == "mine":
        customers = customers.filter(owner=request.user)
    else:
        view = "all"

    if status in Customer.Status.values:
        customers = customers.filter(status=status)
    else:
        status = ""

    # Every word must match at least one field, so "ana lisboa" finds Ana in Lisboa.
    for term in query.split():
        term_filter = Q()
        for field in SEARCH_FIELDS:
            term_filter |= Q(**{f"{field}__icontains": term})
        customers = customers.filter(term_filter)

    descending = sort.startswith("-")
    sort_key = sort.lstrip("-")
    if sort_key not in SORT_COLUMNS:
        sort_key, descending = "name", False
    order_fields = SORT_COLUMNS[sort_key][1]
    customers = customers.order_by(*[f"-{f}" if descending else f for f in order_fields])

    columns = [
        {
            "key": key,
            "label": label,
            "active": key == sort_key,
            "descending": key == sort_key and descending,
            # Clicking the active column flips the direction.
            "next_sort": f"-{key}" if key == sort_key and not descending else key,
        }
        for key, (label, _) in SORT_COLUMNS.items()
    ]

    page = Paginator(customers, PAGE_SIZE).get_page(request.GET.get("page"))
    return render(
        request,
        "customers/customer_list.html",
        {
            "page": page,
            "query": query,
            "view": view,
            "status": status,
            "status_choices": Customer.Status.choices,
            "columns": {c["key"]: c for c in columns},
            "sort_label": SORT_COLUMNS[sort_key][0],
            "sort_descending": descending,
        },
    )


@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer.objects.select_related("owner", "created_by"), pk=pk)
    return render(request, "customers/customer_detail.html", detail_context(customer))


def detail_context(customer, activity_form=None):
    pipeline = list(Customer.PIPELINE)
    current_index = pipeline.index(customer.status) if customer.status in pipeline else -1
    path = [
        {
            "value": value,
            "label": Customer.Status(value).label,
            "state": "current" if i == current_index else "done" if i < current_index else "todo",
        }
        for i, value in enumerate(pipeline)
    ]
    next_stage = None
    if 0 <= current_index < len(pipeline) - 1:
        value = pipeline[current_index + 1]
        next_stage = {"value": value, "label": Customer.Status(value).label}

    return {
        "customer": customer,
        "path": path,
        "next_stage": next_stage,
        "activities": customer.activities.select_related("created_by"),
        "activity_form": activity_form or ActivityForm(),
    }


@login_required
def customer_create(request):
    form = CustomerForm(request.POST or None, initial={"owner": request.user})
    if request.method == "POST" and form.is_valid():
        customer = form.save(commit=False)
        customer.created_by = request.user
        customer.save()
        messages.success(request, f"{customer.full_name} was created.")
        return redirect(customer)

    return render(request, "customers/customer_form.html", {"form": form})


@login_required
def customer_update(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    old_status = customer.status
    form = CustomerForm(request.POST or None, instance=customer)
    if request.method == "POST" and form.is_valid():
        customer = form.save()
        if customer.status != old_status:
            log_status_change(customer, old_status, request.user)
        messages.success(request, f"{customer.full_name} was saved.")
        return redirect(customer)

    return render(
        request, "customers/customer_form.html", {"form": form, "customer": customer}
    )


@login_required
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    # Deleting only happens on POST, from the confirmation page.
    if request.method == "POST":
        name = customer.full_name
        customer.delete()
        messages.success(request, f"{name} was deleted.")
        return redirect("customers:list")

    return render(request, "customers/customer_confirm_delete.html", {"customer": customer})


@login_required
@require_POST
def customer_set_status(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    new_status = request.POST.get("status")
    if new_status not in Customer.Status.values:
        messages.error(request, "That status doesn't exist.")
        return redirect(customer)

    if new_status != customer.status:
        old_status = customer.status
        customer.status = new_status
        customer.save(update_fields=["status", "updated_at"])
        log_status_change(customer, old_status, request.user)
        messages.success(request, f"Status changed to {customer.get_status_display()}.")
    return redirect(customer)


@login_required
@require_POST
def activity_create(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    form = ActivityForm(request.POST)
    if form.is_valid():
        activity = form.save(commit=False)
        activity.customer = customer
        activity.created_by = request.user
        activity.save()
        messages.success(request, f"{activity.get_kind_display()} logged.")
        return redirect(f"{customer.get_absolute_url()}#activity")

    # Show the record again with the form errors.
    return render(
        request,
        "customers/customer_detail.html",
        detail_context(customer, activity_form=form),
        status=400,
    )


def log_status_change(customer, old_status, user):
    Activity.objects.create(
        customer=customer,
        kind=Activity.Kind.STATUS,
        subject=f"{Customer.Status(old_status).label} → {customer.get_status_display()}",
        created_by=user,
    )
