from django.contrib import admin
from .models import Salon, Service

# Register your models here.

@admin.register(Salon)
class SalonAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "opening_time", "closing_time")


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "duration_minutes", "is_active")
    list_filter = ("is_active",)
