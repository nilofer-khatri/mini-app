from django.db import models
from django.db.models import Sum
from salon.models import Service


class Booking(models.Model):
    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Cash"
        ONLINE = "online", "Online"

    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        PAID = "paid", "Paid"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"

    customer_name = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=20)
    date = models.DateField()
    time = models.TimeField()
    services = models.ManyToManyField(Service, related_name="bookings")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(
        max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.CASH
    )
    payment_status = models.CharField(
        max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "time"]
        indexes = [models.Index(fields=["date", "time"])]

    def calculate_total(self):
        return self.services.aggregate(t=Sum("price"))["t"] or 0

    def __str__(self):
        return f"{self.customer_name} - {self.date} {self.time.strftime('%I:%M %p')}"