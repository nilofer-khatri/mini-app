import tempfile
from datetime import datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from salon.models import Salon, Service
from .availability import build_availability
from .forms import BookingForm
from .models import Booking


class BaseSalonTest(TestCase):
    def setUp(self):
        self.salon = Salon.objects.create(
            name="Test Salon", phone="9876543210", address="Test street",
            opening_time=time(9, 0), closing_time=time(20, 0), slot_minutes=30,
        )
        self.haircut = Service.objects.create(name="Haircut", price=Decimal("150"))
        self.facial = Service.objects.create(name="Facial", price=Decimal("250"))
        self.today = timezone.localdate()
        self.tomorrow = self.today + timedelta(days=1)

    def booking_data(self, **overrides):
        data = {
            "customer_name": "Test Customer",
            "customer_phone": "9876543210",
            "date": self.tomorrow.isoformat(),
            "time": "10:00",
            "services": [self.haircut.pk],
            "payment_method": "cash",
        }
        data.update(overrides)
        return data

    def make_form(self, **overrides):
        return BookingForm(self.booking_data(**overrides), salon=self.salon)


class BookingFormTests(BaseSalonTest):
    def test_total_is_calculated_on_the_server(self):
        form = self.make_form(services=[self.haircut.pk, self.facial.pk])
        self.assertTrue(form.is_valid(), form.errors)
        booking = form.save()
        booking.refresh_from_db()
        self.assertEqual(booking.total_amount, Decimal("400"))

    def test_one_person_salon_rejects_a_second_booking(self):
        first = self.make_form()
        self.assertTrue(first.is_valid(), first.errors)
        first.save()

        second = self.make_form(customer_name="Someone Else")
        self.assertFalse(second.is_valid())
        self.assertIn("fully booked", str(second.errors))

    def test_salon_with_two_staff_allows_two_bookings_but_not_three(self):
        self.salon.staff_count = 2
        self.salon.save()

        for name in ("First", "Second"):
            form = self.make_form(customer_name=name)
            self.assertTrue(form.is_valid(), form.errors)
            form.save()

        third = self.make_form(customer_name="Third")
        self.assertFalse(third.is_valid())
        self.assertIn("fully booked", str(third.errors))

    def test_cancelled_slot_can_be_booked_again(self):
        first = self.make_form()
        self.assertTrue(first.is_valid(), first.errors)
        first.save()
        Booking.objects.update(status=Booking.Status.CANCELLED)

        second = self.make_form(customer_name="Someone Else")
        self.assertTrue(second.is_valid(), second.errors)

    def test_past_date_is_rejected(self):
        yesterday = self.today - timedelta(days=1)
        form = self.make_form(date=yesterday.isoformat())
        self.assertFalse(form.is_valid())
        self.assertIn("date", form.errors)

    def test_time_that_already_passed_today_is_rejected(self):
        fixed_now = timezone.make_aware(datetime.combine(self.today, time(15, 0)))
        with mock.patch("bookings.forms.timezone.localtime", return_value=fixed_now):
            early = self.make_form(date=self.today.isoformat(), time="10:00")
            self.assertFalse(early.is_valid())
            later = self.make_form(date=self.today.isoformat(), time="16:00")
            self.assertTrue(later.is_valid(), later.errors)

    def test_bad_phone_number_is_rejected(self):
        form = self.make_form(customer_phone="abc")
        self.assertFalse(form.is_valid())
        self.assertIn("customer_phone", form.errors)

    def test_phone_number_is_cleaned(self):
        form = self.make_form(customer_phone="98765 43210")
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["customer_phone"], "9876543210")


class BookingModelTests(BaseSalonTest):
    def test_calculate_total(self):
        booking = Booking.objects.create(
            customer_name="A", customer_phone="9876543210",
            date=self.tomorrow, time=time(10, 0),
        )
        booking.services.add(self.haircut, self.facial)
        self.assertEqual(booking.calculate_total(), Decimal("400"))


class AvailabilityTests(BaseSalonTest):
    def slots_for_tomorrow(self):
        days = build_availability(self.salon)
        day = next(d for d in days if d["iso"] == self.tomorrow.isoformat())
        return {s["value"]: s for _, group in day["groups"] for s in group}

    def test_booked_slot_is_marked_booked(self):
        Booking.objects.create(
            customer_name="A", customer_phone="9876543210",
            date=self.tomorrow, time=time(12, 0),
        )
        slots = self.slots_for_tomorrow()
        self.assertTrue(slots["12:00"]["booked"])
        self.assertFalse(slots["12:30"]["booked"])

    def test_slot_stays_free_until_all_staff_are_booked(self):
        self.salon.staff_count = 2
        self.salon.save()
        Booking.objects.create(
            customer_name="A", customer_phone="9876543210",
            date=self.tomorrow, time=time(12, 0),
        )
        self.assertFalse(self.slots_for_tomorrow()["12:00"]["booked"])

        Booking.objects.create(
            customer_name="B", customer_phone="9876543211",
            date=self.tomorrow, time=time(12, 0),
        )
        self.assertTrue(self.slots_for_tomorrow()["12:00"]["booked"])

    def test_strip_starts_today_then_tomorrow(self):
        days = build_availability(self.salon)
        self.assertEqual(days[0]["label"], "Today")
        self.assertEqual(days[1]["label"], "Tomorrow")


class ViewTests(BaseSalonTest):
    def test_home_page_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_booking_through_the_page_saves_and_updates_excel(self):
        with tempfile.TemporaryDirectory() as tmp:
            excel_path = Path(tmp) / "bookings.xlsx"
            with self.settings(EXCEL_EXPORT_PATH=excel_path):
                response = self.client.post("/", self.booking_data())
                self.assertRedirects(response, "/booked/")
                self.assertEqual(Booking.objects.count(), 1)
                self.assertTrue(excel_path.exists())

    def test_success_page_without_a_booking_goes_home(self):
        response = self.client.get("/booked/")
        self.assertRedirects(response, "/", fetch_redirect_response=False)

    def test_dashboard_needs_a_staff_login(self):
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 302)

    def test_dashboard_opens_for_staff(self):
        User.objects.create_user("owner", password="pass12345", is_staff=True)
        self.client.login(username="owner", password="pass12345")
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)