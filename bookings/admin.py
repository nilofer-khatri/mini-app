from django.contrib import admin
from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "customer_name", "customer_phone", "date", "time",
        "total_amount", "payment_method", "payment_status", "status",
    )
    list_filter = ("date", "status", "payment_status", "payment_method")
    search_fields = ("customer_name", "customer_phone")
    filter_horizontal = ("services",)
    readonly_fields = ("total_amount",)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        booking = form.instance
        booking.total_amount = booking.calculate_total()
        booking.save(update_fields=["total_amount"])