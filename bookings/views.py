from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render

from salon.models import Salon, Service
from .availability import build_availability
from .excel import export_bookings_to_excel
from .forms import BookingForm
from .models import Booking


def home(request):
    salon = Salon.objects.first()
    if request.method == "POST":
        form = BookingForm(request.POST, salon=salon)
        if form.is_valid():
            try:
                booking = form.save()
            except IntegrityError:
                form.add_error(None, "Sorry, that slot was just taken. Please choose another.")
            else:
                export_bookings_to_excel()
                request.session["last_booking"] = booking.pk
                return redirect("booking_success")
    else:
        form = BookingForm(salon=salon)

    context = {
        "salon": salon,
        "form": form,
        "services": Service.objects.filter(is_active=True),
        "days": build_availability(salon),
    }
    return render(request, "bookings/home.html", context)


def success(request):
    pk = request.session.get("last_booking")
    if not pk:
        return redirect("home")
    booking = get_object_or_404(Booking, pk=pk)
    return render(
        request,
        "bookings/success.html",
        {"booking": booking, "salon": Salon.objects.first()},
    )