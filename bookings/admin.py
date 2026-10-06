from django.contrib import admin
from django.http import HttpResponse

from .excel import build_workbook, export_bookings_to_excel
from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "customer_name", "customer_phone", "date", "time",
        "total_amount", "payment_method", "payment_status", "status",
    )
    # These two columns can be changed right in the list (press Save at the bottom)
    list_editable = ("payment_status", "status")
    list_filter = ("date", "status", "payment_status", "payment_method")
    search_fields = ("customer_name", "customer_phone")
    filter_horizontal = ("services",)
    readonly_fields = ("total_amount",)
    actions = ["mark_paid", "mark_unpaid", "mark_confirmed", "mark_cancelled", "download_excel"]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        booking = form.instance
        booking.total_amount = booking.calculate_total()
        booking.save(update_fields=["total_amount"])
        export_bookings_to_excel()

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        export_bookings_to_excel()

    def delete_queryset(self, request, queryset):
        super().delete_queryset(request, queryset)
        export_bookings_to_excel()

    def _bulk_update(self, request, queryset, label, **fields):
        count = queryset.update(**fields)
        export_bookings_to_excel()
        self.message_user(request, f"{count} booking(s) marked as {label}.")

    @admin.action(description="Mark selected as Paid")
    def mark_paid(self, request, queryset):
        self._bulk_update(request, queryset, "Paid", payment_status=Booking.PaymentStatus.PAID)

    @admin.action(description="Mark selected as Unpaid")
    def mark_unpaid(self, request, queryset):
        self._bulk_update(request, queryset, "Unpaid", payment_status=Booking.PaymentStatus.UNPAID)

    @admin.action(description="Mark selected as Confirmed")
    def mark_confirmed(self, request, queryset):
        self._bulk_update(request, queryset, "Confirmed", status=Booking.Status.CONFIRMED)

    @admin.action(description="Cancel selected bookings")
    def mark_cancelled(self, request, queryset):
        self._bulk_update(request, queryset, "Cancelled", status=Booking.Status.CANCELLED)

    @admin.action(description="Download selected bookings as Excel")
    def download_excel(self, request, queryset):
        wb = build_workbook(queryset)
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = 'attachment; filename="bookings.xlsx"'
        wb.save(response)
        return response