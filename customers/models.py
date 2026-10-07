from django.conf import settings
from django.db import models
from django.urls import reverse


class Customer(models.Model):
    class Status(models.TextChoices):
        LEAD = "lead", "Lead"
        CONTACTED = "contacted", "Contacted"
        QUALIFIED = "qualified", "Qualified"
        CUSTOMER = "customer", "Customer"
        INACTIVE = "inactive", "Inactive"

    # Stages shown on the record page "path", in order.
    PIPELINE = [Status.LEAD, Status.CONTACTED, Status.QUALIFIED, Status.CUSTOMER]
    OPEN_STATUSES = [Status.LEAD, Status.CONTACTED, Status.QUALIFIED]

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    company = models.CharField(max_length=120, blank=True)
    job_title = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.LEAD)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customers_owned",
    )

    email = models.EmailField(max_length=254)
    phone = models.CharField(max_length=30)
    address = models.CharField(max_length=150)
    city = models.CharField(max_length=60)
    state = models.CharField("state / region", max_length=60, blank=True)
    zipcode = models.CharField("postal code", max_length=15)
    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customers_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def initials(self):
        return f"{self.first_name[:1]}{self.last_name[:1]}".upper()

    @property
    def is_open(self):
        return self.status in self.OPEN_STATUSES

    def get_absolute_url(self):
        return reverse("customers:detail", args=[self.pk])


class Activity(models.Model):
    class Kind(models.TextChoices):
        CALL = "call", "Call"
        EMAIL = "email", "Email"
        MEETING = "meeting", "Meeting"
        NOTE = "note", "Note"
        STATUS = "status", "Status change"

    ICONS = {
        "call": "bi-telephone",
        "email": "bi-envelope",
        "meeting": "bi-people",
        "note": "bi-journal-text",
        "status": "bi-flag",
    }

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="activities")
    kind = models.CharField("type", max_length=20, choices=Kind.choices, default=Kind.CALL)
    subject = models.CharField(max_length=200)
    details = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activities",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name_plural = "activities"

    def __str__(self):
        return f"{self.get_kind_display()}: {self.subject}"

    @property
    def icon(self):
        return self.ICONS.get(self.kind, "bi-dot")
