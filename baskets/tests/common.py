import random
import string
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver

from baskets.models import Delivery, Order, Producer, Product

User = get_user_model()


def get_random_string():
    LENGTH = 10
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for _ in range(LENGTH))


def create_user(is_staff=False):
    username = f"test_user_{get_random_string()}"
    return User.objects.create(
        username=username,
        email=f"{username}@baskets.com",
        is_staff=is_staff,
    )


def create_producer():
    return Producer.objects.create(name=get_random_string())


def create_product(producer=None):
    initial_products_count = Product.objects.count()
    if not producer:
        producer = create_producer()
    product = Product.objects.create(
        producer=producer,
        name=get_random_string(),
        unit_price=Decimal(random.randint(0, 10000)) / 100,
    )
    assert Product.objects.count() == initial_products_count + 1
    assert product.is_active
    return product


def create_opened_delivery(products=None):
    today = date.today()
    existing_deliveries_count = Delivery.objects.count()
    delivery = Delivery.objects.create(
        date=today
        + timedelta(
            days=existing_deliveries_count
        ),  # can't have more than one delivery per day
        order_deadline=today,
        message=f"opened delivery {existing_deliveries_count + 1}",
    )
    assert delivery.is_open
    if not products:
        products = [create_product()]
    delivery.products.set(products)
    return delivery


def create_closed_delivery(products=None):
    today = date.today()
    d_date = today - timedelta(days=Delivery.objects.count())
    delivery = Delivery.objects.create(
        date=d_date,
        order_deadline=d_date - timedelta(days=2),
        message="closed delivery",
    )
    assert not delivery.is_open
    if not products:
        products = [create_product()]
    delivery.products.set(products)
    return delivery


def create_order_item(delivery, product=None, user=None):
    if not product:
        product = delivery.products.first()
    if not user:
        user = create_user()
    order = Order.objects.create(user=user, delivery=delivery)
    order_item = order.items.create(product=product, quantity=random.randint(1, 9))
    assert order.items.count() == 1
    return order_item


class SeleniumTestCase(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.driver = webdriver.Chrome()
        cls.driver.maximize_window()
        cls.driver.implicitly_wait(10)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()
