from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"deliveries", views.DeliveryViewSet, "delivery")
router.register(r"orders", views.OrderViewSet, "order")

urlpatterns = [path("v1/", include(router.urls))]
