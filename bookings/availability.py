from collections import Counter
from datetime import datetime, time, timedelta

from django.utils import timezone

from .models import Booking

DAYS_AHEAD = 7  # how many days the day strip shows (Today, Tomorrow, ...)


def capacity_of(salon):
    return salon.staff_count if salon else 1


def slot_is_full(salon, day, slot_time):
    """True when the slot already has as many active bookings as the salon has staff."""
    taken = (
        Booking.objects.filter(date=day, time=slot_time)
        .exclude(status=Booking.Status.CANCELLED)
        .count()
    )
    return taken >= capacity_of(salon)


def day_label(day, today):
    if day == today:
        return "Today"
    if day == today + timedelta(days=1):
        return "Tomorrow"
    return day.strftime("%a")


def period_of(t):
    if t.hour < 12:
        return "Morning"
    if t.hour < 17:
        return "Afternoon"
    return "Evening"


def build_availability(salon):
    """Return one entry per day, with Morning/Afternoon/Evening slots marked booked or free."""
    now = timezone.localtime()
    today = now.date()
    capacity = capacity_of(salon)

    start = salon.opening_time if salon else time(9, 0)
    end = salon.closing_time if salon else time(20, 0)
    step = salon.slot_minutes if salon else 30

    last_day = today + timedelta(days=DAYS_AHEAD - 1)
    counts = Counter(
        Booking.objects.filter(date__range=(today, last_day))
        .exclude(status=Booking.Status.CANCELLED)
        .values_list("date", "time")
    )

    days = []
    for offset in range(DAYS_AHEAD):
        day = today + timedelta(days=offset)
        groups = {"Morning": [], "Afternoon": [], "Evening": []}

        current = datetime.combine(day, start)
        end_dt = datetime.combine(day, end)
        while current < end_dt:
            slot_time = current.time()
            # Slots that have already passed today are hidden
            if not (day == today and slot_time <= now.time()):
                groups[period_of(slot_time)].append({
                    "value": current.strftime("%H:%M"),
                    "label": current.strftime("%I:%M %p"),
                    "booked": counts[(day, slot_time)] >= capacity,
                })
            current += timedelta(minutes=step)

        days.append({
            "iso": day.isoformat(),
            "label": day_label(day, today),
            "short_date": day.strftime("%d %b"),
            "groups": [(name, slots) for name, slots in groups.items() if slots],
            "free_count": sum(
                1 for slots in groups.values() for s in slots if not s["booked"]
            ),
        })
    return days