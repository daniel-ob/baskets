from django.urls import path

from . import views

app_name = "baskets"
urlpatterns = [
    path("", views.index, name="index"),  # 'next orders' page
    path("history/", views.order_history, name="order_history"),
    path("contact/", views.contact, name="contact"),

    # API Routes
    path("orders", views.orders, name="orders"),
    path("orders/<int:order_id>", views.order, name="order"),
    path("deliveries", views.deliveries, name="deliveries"),
    path("deliveries/<int:delivery_id>", views.delivery, name="delivery"),

    # Staff exports
    path("deliveries/<int:delivery_id>/export", views.delivery_export, name="delivery_export"),
    path("orders/export", views.order_export, name="order_export"),
    path("producers/export", views.producer_export, name="producer_export"),
]
