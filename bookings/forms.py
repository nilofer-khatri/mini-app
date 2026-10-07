import re
from datetime import datetime, time, timedelta

from django import forms
from django.utils import timezone

from salon.models import Service
from .availability import slot_is_full
from .models import Booking


def time_choices(salon):
    """Time slots grouped as Morning / Afternoon / Evening, shown as hh:mm AM/PM."""
    start = salon.opening_time if salon else time(9, 0)
    end = salon.closing_time if salon else time(20, 0)
    step = salon.slot_minutes if salon else 30

    groups = {"Morning": [], "Afternoon": [], "Evening": []}
    base = timezone.localdate()
    current = datetime.combine(base, start)
    end_dt = datetime.combine(base, end)
    while current < end_dt:
        slot = (current.strftime("%H:%M"), current.strftime("%I:%M %p"))
        if current.hour < 12:
            groups["Morning"].append(slot)
        elif current.hour < 17:
            groups["Afternoon"].append(slot)
        else:
            groups["Evening"].append(slot)
        current += timedelta(minutes=step)

    choices = [("", "Select a time")]
    choices += [(label, slots) for label, slots in groups.items() if slots]
    return choices


class ServiceCheckboxes(forms.CheckboxSelectMultiple):
    """Checkboxes that carry each service's price, for the live total."""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        option["attrs"]["data-price"] = str(value.instance.price)
        return option


class ServiceChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.name} — ₹{obj.price:.0f}"


class BookingForm(forms.ModelForm):
    services = ServiceChoiceField(
        queryset=Service.objects.filter(is_active=True),
        widget=ServiceCheckboxes,
    )
    time = forms.TimeField(widget=forms.Select)

    class Meta:
        model = Booking
        fields = [
            "customer_name", "customer_phone", "date",
            "time", "services", "payment_method",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "customer_phone": forms.TextInput(attrs={"type": "tel", "inputmode": "tel"}),
        }

    def __init__(self, *args, salon=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.salon = salon
        self.fields["time"].widget.choices = time_choices(salon)
        self.fields["date"].widget.attrs["min"] = timezone.localdate().isoformat()
        self.initial.setdefault("date", timezone.localdate())

        base = (
            "w-full min-w-0 max-w-full rounded-lg border border-gray-300 px-3 py-3 "
            "text-base focus:outline-none focus:ring-2 focus:ring-brand-400"
        )
        for name, field in self.fields.items():
            if name != "services":
                field.widget.attrs["class"] = base

    def clean_customer_phone(self):
        raw = self.cleaned_data["customer_phone"]
        phone = re.sub(r"[\s\-()]", "", raw)
        if not re.fullmatch(r"\+?\d{10,13}", phone):
            raise forms.ValidationError("Enter a valid phone number (10 to 13 digits).")
        return phone

    def clean_date(self):
        chosen = self.cleaned_data["date"]
        if chosen < timezone.localdate():
            raise forms.ValidationError("Please choose today or a future date.")
        return chosen

    def clean(self):
        cleaned = super().clean()
        chosen_date = cleaned.get("date")
        chosen_time = cleaned.get("time")
        if chosen_date and chosen_time:
            now = timezone.localtime()
            if chosen_date == now.date() and chosen_time <= now.time():
                raise forms.ValidationError(
                    "That time has already passed. Please choose a later slot."
                )
            if slot_is_full(self.salon, chosen_date, chosen_time):
                raise forms.ValidationError(
                    "Sorry, that time slot is fully booked. Please choose another."
                )
        return cleaned

    def save(self, commit=True):
        booking = super().save(commit=False)
        # The server works out the total from database prices, not from the browser
        booking.total_amount = sum(s.price for s in self.cleaned_data["services"])
        if commit:
            booking.save()
            self.save_m2m()
        return booking