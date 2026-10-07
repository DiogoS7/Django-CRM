from django.contrib import admin

from .models import Activity, Customer


class ActivityInline(admin.TabularInline):
    model = Activity
    extra = 0
    fields = ("kind", "subject", "created_by", "created_at")
    readonly_fields = ("created_by", "created_at")


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("full_name", "company", "status", "owner", "email", "city", "created_at")
    list_filter = ("status", "owner", "city")
    search_fields = ("first_name", "last_name", "company", "email", "phone", "city")
    readonly_fields = ("created_by", "created_at", "updated_at")
    inlines = [ActivityInline]


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("subject", "kind", "customer", "created_by", "created_at")
    list_filter = ("kind",)
    search_fields = ("subject", "customer__first_name", "customer__last_name")
