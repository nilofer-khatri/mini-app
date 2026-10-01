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
    list_filter = ("date", "status", "payment_status", "payment_method")
    search_fields = ("customer_name", "customer_phone")
    filter_horizontal = ("services",)
    readonly_fields = ("total_amount",)
    actions = ["download_excel"]

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

    @admin.action(description="Download selected bookings as Excel")
    def download_excel(self, request, queryset):
        wb = build_workbook(queryset)
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = 'attachment; filename="bookings.xlsx"'
        wb.save(response)
        return response