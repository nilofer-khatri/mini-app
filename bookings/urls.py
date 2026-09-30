from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("booked/", views.success, name="booking_success"),
]