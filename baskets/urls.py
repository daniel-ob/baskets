from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"deliveries", views.DeliveryViewSet, "delivery")
router.register(r"orders", views.OrderViewSet, "order")

urlpatterns = [
    path("", views.IndexPageView.as_view(), name="index"),  # 'next orders' page
    path("history/", views.OrderHistoryPageView.as_view(), name="order_history"),
    path("contact/", views.ContactPageView.as_view(), name="contact"),

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
