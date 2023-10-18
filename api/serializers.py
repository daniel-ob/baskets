from rest_framework import serializers
from rest_framework.fields import empty

from baskets.models import Delivery, Order, OrderItem, Producer, Product


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
            queryset = obj.products.filter(id__in=self.products_filter)
        serializer = ProductSerializer(queryset, many=True)
        return serializer.data

    def __init__(self, instance=None, data=empty, products_filter=None, **kwargs):
        super().__init__(instance, data, **kwargs)
        self.products_filter = products_filter


class DeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = Delivery
        fields = ["url", "date", "order_deadline"]


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


class OrderItemSerializer(serializers.ModelSerializer):
    read_only_fields = ["product_name", "product_unit_price", "amount"]

    class Meta:
        model = OrderItem
        fields = ["product", "product_name", "product_unit_price", "quantity", "amount"]


class OrderSerializer(serializers.ModelSerializer):
    delivery = DeliverySerializer(read_only=True)

    class Meta:
        model = Order
        fields = ["url", "delivery", "amount", "is_open"]


class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    read_only_fields = ["amount", "is_open"]

    class Meta:
        model = Order
        fields = ["url", "delivery", "items", "amount", "message", "is_open"]

    def validate_delivery(self, value):
        if not value.is_open:
            raise serializers.ValidationError(
                "Delivery closed (order deadline is past)"
            )
        # only for "create" action
        if not self.instance and value.orders.filter(user=self.context["request"].user):
            raise serializers.ValidationError(
                "You have already an order for this delivery"
            )
        return value

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Order must contain at least one item")
        return value

    def validate(self, data):
        """Check that all items are available on delivery"""

        for item in data["items"]:
            product = item["product"]
            if product not in data["delivery"].products.all():
                raise serializers.ValidationError(
                    {"items": f"Product '{product}' not available in delivery"}
                )
        return data

    def create(self, validated_data):
        # Validations are done before create
        items_data = validated_data.pop("items")
        order = Order.objects.create(
            user=self.context["request"].user, **validated_data
        )
        for item_data in items_data:
            order.items.create(**item_data)
        return order

    def update(self, instance, validated_data):
        # remove previous items, before instance.save() otherwise we get `save() prohibited` error
        for item in instance.items.all():
            item.delete()

        instance.delivery = validated_data.get("delivery", instance.delivery)
        instance.message = validated_data.get("message", instance.message)
        instance.save()

        for item_data in validated_data["items"]:
            instance.items.create(**item_data)

        return instance
