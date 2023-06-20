from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"deliveries", views.DeliveryViewSet, "delivery")
router.register(r"orders", views.OrderViewSet, "order")

urlpatterns = [
    path("", views.index, name="index"),  # 'next orders' page
    path("history/", views.order_history, name="order_history"),
    path("contact/", views.ContactFormView.as_view(), name="contact"),

    # API Routes
    path("api/v1/", include(router.urls)),

    # Staff exports
    path(
        "deliveries/<int:delivery_id>/export",
        views.delivery_export,
        name="delivery_export",
    ),
    path("orders/export", views.order_export, name="order_export"),
    path("producers/export", views.producer_export, name="producer_export"),
]
