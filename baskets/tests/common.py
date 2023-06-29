import random
import string
from datetime import date, timedelta

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from rest_framework.test import APIClient

from baskets.models import Producer, Product, Delivery, Order, OrderItem

User = get_user_model()


def get_random_string():
    LENGTH = 10
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for _ in range(LENGTH))


def create_producer():
    return Producer.objects.create(name=get_random_string())


def create_product(producer=None):
    initial_products_count = Product.objects.count()
    if not producer:
        producer = create_producer()
    product = Product.objects.create(
        producer=producer, name=get_random_string(), unit_price=0.50
    )
    assert Product.objects.count() == initial_products_count + 1
    assert product.is_active
    return product


def create_opened_delivery(products=None):
    today = date.today()
    delivery = Delivery.objects.create(
        date=today + timedelta(days=7),
        order_deadline=today + timedelta(days=6),
        message="opened delivery",
    )
    assert delivery.is_open
    if products:
        delivery.products.set(products)
    return delivery


def create_closed_delivery(products=None):
    today = date.today()
    delivery = Delivery.objects.create(
        date=today - timedelta(days=7),
        order_deadline=today - timedelta(days=8),
        message="closed delivery",
    )
    assert not delivery.is_open
    if products:
        delivery.products.set(products)
    return delivery


def create_order_item(delivery, product):
    order = Order.objects.create(
        user=User.objects.create(username=f"test_user_{get_random_string()}"),
        delivery=delivery,
    )
    order_item = order.items.create(product=product, quantity=4)
    assert order.items.count() == 1
    return order_item


class BasketsTestCase(TestCase):
    def setUp(self):
        """Define initial data for every Baskets test"""

        # Create users
        self.u1 = User.objects.create_user(
            username="user1",
            first_name="test",
            last_name="user",
            email="user1@baskets.com",
            phone="0123456789",
            address="my street, my city",
            password="secret",
        )
        EmailAddress.objects.create(
            user=self.u1, email=self.u1.email, verified=True
        )  # verify user email address, so he can directly log in on test_functional
        self.u2 = User.objects.create(username="user2")

        # Create producers
        self.producer1 = Producer.objects.create(name="producer1")
        self.producer2 = Producer.objects.create(name="producer2")
        self.producer3 = Producer.objects.create(
            name="producer3"
        )  # not present in deliveries

        # Create products
        self.product1 = Product.objects.create(
            producer=self.producer1, name="product1", unit_price=0.50
        )
        self.product2 = Product.objects.create(
            producer=self.producer1, name="product2", unit_price=1.00
        )
        self.product3 = Product.objects.create(
            producer=self.producer2, name="product3", unit_price=1.15
        )
        self.product4 = Product.objects.create(
            producer=self.producer3, name="product4", unit_price=15.30
        )

        # Create deliveries
        today = date.today()
        tomorrow = today + timedelta(days=1)
        after_tomorrow = today + timedelta(days=2)
        yesterday = today - timedelta(days=1)
        # closed delivery
        self.d1 = Delivery.objects.create(
            date=today, order_deadline=yesterday, message="delivery 1"
        )
        self.d1.products.set([self.product1, self.product2])
        # opened deliveries
        self.d2 = Delivery.objects.create(
            date=tomorrow, order_deadline=today, message="delivery 2"
        )
        self.d2.products.set([self.product1, self.product3])
        self.d3 = Delivery.objects.create(
            date=after_tomorrow, order_deadline=tomorrow, message="delivery 3"
        )
        self.d3.products.set([self.product1, self.product2, self.product3])

        # Create orders
        self.o1 = Order.objects.create(
            user=self.u1, delivery=self.d1, message="order 1"
        )  # closed, 3.00
        self.o2 = Order.objects.create(
            user=self.u1, delivery=self.d2, message="order 2"
        )  # opened, 3.95
        self.o3 = Order.objects.create(
            user=self.u2, delivery=self.d2, message="order 3"
        )  # opened, 1.00

        # Create order items
        self.o1i1 = OrderItem.objects.create(
            order=self.o1, product=self.product1, quantity=4
        )  # 2.00
        self.o1i2 = OrderItem.objects.create(
            order=self.o1, product=self.product2, quantity=1
        )  # 1.00
        self.o2i1 = OrderItem.objects.create(
            order=self.o2, product=self.product1, quantity=1
        )  # 0.50
        self.o2i2 = OrderItem.objects.create(
            order=self.o2, product=self.product3, quantity=3
        )  # 3.45
        self.o3i1 = OrderItem.objects.create(
            order=self.o3, product=self.product1, quantity=2
        )  # 1.00

        # Create test clients
        self.c = Client()
        self.api_c = APIClient()
