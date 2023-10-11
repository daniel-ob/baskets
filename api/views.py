from datetime import date

from rest_framework import viewsets, status
from rest_framework.response import Response

from .serializers import (
    DeliverySerializer,
    DeliveryDetailSerializer,
    OrderSerializer,
    OrderDetailSerializer,
)
from baskets.models import Delivery


class DeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    """Opened Deliveries API"""

    serializer_class = DeliverySerializer
    detail_serializer_class = DeliveryDetailSerializer
    queryset = Delivery.objects.filter(order_deadline__gte=date.today()).order_by(
        "date"
    )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return self.detail_serializer_class
        return super().get_serializer_class()


class OrderViewSet(viewsets.ModelViewSet):
    """User orders API"""

    serializer_class = OrderSerializer
    detail_serializer_class = OrderDetailSerializer

    def get_queryset(self):
        return self.request.user.orders.all().order_by("-delivery__date")

    def get_serializer_class(self):
        if self.action in ["retrieve", "create", "update"]:
            return self.detail_serializer_class
        return super().get_serializer_class()

    def destroy(self, request, *args, **kwargs):
        """prevent closed orders deletion"""

        order = self.get_object()
        if not order.is_open:
            return Response(
                data={"message": "order deadline is past"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_destroy(order)
        return Response(status=status.HTTP_204_NO_CONTENT)
