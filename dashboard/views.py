import calendar
from datetime import datetime, timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum
from django.shortcuts import render
from django.utils import timezone

from bookings.models import Booking
from salon.models import Service


def parse_month(value):
    """Turn '2026-10' into the first day of that month; default to the current month."""
    try:
        return datetime.strptime(value, "%Y-%m").date()
    except (TypeError, ValueError):
        return timezone.localdate().replace(day=1)


def money(queryset):
    return queryset.aggregate(t=Sum("total_amount"))["t"] or 0


@staff_member_required
def monthly(request):
    first = parse_month(request.GET.get("month"))
    prev_month = (first - timedelta(days=1)).replace(day=1)
    next_month = (first + timedelta(days=32)).replace(day=1)

    month_qs = Booking.objects.filter(date__year=first.year, date__month=first.month)
    active = month_qs.exclude(status=Booking.Status.CANCELLED)

    method_names = dict(Booking.PaymentMethod.choices)
    by_method = [
        {
            "name": method_names.get(row["payment_method"], row["payment_method"]),
            "count": row["n"],
            "amount": row["amount"] or 0,
        }
        for row in active.values("payment_method")
        .annotate(n=Count("id"), amount=Sum("total_amount"))
        .order_by("payment_method")
    ]

    popular = list(
        Service.objects.filter(bookings__in=active)
        .annotate(times=Count("bookings"))
        .order_by("-times", "name")[:5]
    )

    # One entry for every day of the month, with zeros on days without bookings
    daily = {
        row["date"].day: row
        for row in active.values("date").annotate(n=Count("id"), amount=Sum("total_amount"))
    }
    days_in_month = calendar.monthrange(first.year, first.month)[1]
    day_numbers = list(range(1, days_in_month + 1))

    received = money(active.filter(payment_status=Booking.PaymentStatus.PAID))
    pending = money(active.filter(payment_status=Booking.PaymentStatus.UNPAID))

    chart = {
        "days": [str(d) for d in day_numbers],
        "counts": [daily[d]["n"] if d in daily else 0 for d in day_numbers],
        "amounts": [float(daily[d]["amount"] or 0) if d in daily else 0 for d in day_numbers],
        "method_labels": [m["name"] for m in by_method],
        "method_amounts": [float(m["amount"]) for m in by_method],
        "service_labels": [s.name for s in popular],
        "service_counts": [s.times for s in popular],
        "paid": float(received),
        "unpaid": float(pending),
    }

    context = {
        "month": first,
        "prev_month": prev_month.strftime("%Y-%m"),
        "next_month": next_month.strftime("%Y-%m"),
        "total_bookings": active.count(),
        "cancelled": month_qs.filter(status=Booking.Status.CANCELLED).count(),
        "total_amount": money(active),
        "received": received,
        "pending": pending,
        "chart": chart,
    }
    return render(request, "dashboard/monthly.html", context)