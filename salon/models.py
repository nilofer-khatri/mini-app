from django.core.validators import MinValueValidator
from django.db import models


class Salon(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    address = models.TextField()
    opening_time = models.TimeField(default="09:00")
    closing_time = models.TimeField(default="20:00")
    slot_minutes = models.PositiveIntegerField(
        default=30, help_text="Length of one booking slot in minutes"
    )
    staff_count = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="How many customers can be served at the same time (staff or chairs)",
    )

    def __str__(self):
        return self.name


class Service(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    duration_minutes = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} (₹{self.price})"