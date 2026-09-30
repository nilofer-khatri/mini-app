from datetime import date, datetime, time, timedelta

from django import forms

from salon.models import Service
from .models import Booking


def time_choices(salon):
    """Time slots grouped as Morning / Afternoon / Evening, shown as hh:mm AM/PM."""
    start = salon.opening_time if salon else time(9, 0)
    end = salon.closing_time if salon else time(20, 0)
    step = salon.slot_minutes if salon else 30

    groups = {"Morning": [], "Afternoon": [], "Evening": []}
    current = datetime.combine(date.today(), start)
    end_dt = datetime.combine(date.today(), end)
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
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, salon=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["time"].widget.choices = time_choices(salon)
        self.fields["date"].widget.attrs["min"] = date.today().isoformat()
        self.initial.setdefault("date", date.today())

        base = (
            "w-full rounded-lg border border-gray-300 px-3 py-2 "
            "focus:outline-none focus:ring-2 focus:ring-pink-400"
        )
        for name, field in self.fields.items():
            if name != "services":
                field.widget.attrs["class"] = base

    def clean_date(self):
        chosen = self.cleaned_data["date"]
        if chosen < date.today():
            raise forms.ValidationError("Please choose today or a future date.")
        return chosen

    def clean(self):
        cleaned = super().clean()
        chosen_date = cleaned.get("date")
        chosen_time = cleaned.get("time")
        if chosen_date and chosen_time:
            taken = Booking.objects.filter(
                date=chosen_date, time=chosen_time
            ).exclude(status=Booking.Status.CANCELLED)
            if taken.exists():
                raise forms.ValidationError(
                    "Sorry, that time slot is already booked. Please choose another."
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