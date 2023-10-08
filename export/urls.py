from django.urls import path

from . import views

urlpatterns = [
    path("deliveries/<int:delivery_id>", views.delivery_export, name="delivery_export"),
    path("orders", views.order_export, name="order_export"),
    path("producers", views.producer_export, name="producer_export"),
]
