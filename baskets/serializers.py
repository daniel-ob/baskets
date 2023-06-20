from rest_framework import serializers
from rest_framework.fields import empty

from baskets.models import Delivery, Producer, Product


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "unit_price"]


class ProducerSerializer(serializers.ModelSerializer):
    products = serializers.SerializerMethodField()

    class Meta:
        model = Producer
        fields = ["name", "products"]

    def get_products(self, obj):
        queryset = obj.products.all()
        if self.products_filter:
            # filter by delivery.products
            queryset = obj.products.filter(id__in=self.products_filter)
        serializer = ProductSerializer(queryset, many=True)
        return serializer.data

    def __init__(self, instance=None, data=empty, products_filter=None, **kwargs):
        super().__init__(instance, data, **kwargs)
        self.products_filter = products_filter


class DeliveryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Delivery
        fields = ["url", "date"]


class DeliveryDetailSerializer(serializers.ModelSerializer):
    products_by_producer = serializers.SerializerMethodField()

    class Meta:
        model = Delivery
        fields = ["id", "date", "order_deadline", "products_by_producer", "message"]

    def get_products_by_producer(self, obj):
        delivery_products = obj.products.all()
        delivery_producers = Producer.objects.filter(
            products__in=delivery_products
        ).distinct()
        serializer = ProducerSerializer(
            delivery_producers, many=True, products_filter=delivery_products
        )
        return serializer.data
