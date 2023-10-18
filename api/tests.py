import json

from django.db.models import Max
from django.urls import reverse, reverse_lazy
from rest_framework import status
from rest_framework.test import APITestCase

from baskets.models import Order, OrderItem, Product, Delivery, Producer
from baskets.tests.common import (
    create_closed_delivery,
    create_opened_delivery,
    create_order_item,
    create_producer,
    create_product,
    create_user,
)

SERVER_NAME = "http://testserver"


def get_product_json(product):
    return {
        "id": product.id,
        "name": product.name,
        "unit_price": f"{product.unit_price:.2f}",
    }


def get_delivery_json(delivery):
    return {
        "url": SERVER_NAME + reverse("delivery-detail", args=[delivery.id]),
        "date": delivery.date.isoformat(),
        "order_deadline": delivery.order_deadline.isoformat(),
    }


def get_delivery_detail_json(delivery):
    delivery_producers = Producer.objects.filter(
        products__in=delivery.products.all()
    ).distinct()
    return {
        "id": delivery.id,
        "date": delivery.date.isoformat(),
        "order_deadline": delivery.order_deadline.isoformat(),
        "products_by_producer": [
            {
                "name": producer.name,
                "products": [
                    get_product_json(product)
                    for product in producer.products.all().order_by("name")
                    if product in delivery.products.all()
                ],
            }
            for producer in delivery_producers.all().order_by("name")
        ],
        "message": delivery.message,
    }


def get_order_json(order):
    return {
        "url": SERVER_NAME + reverse("order-detail", args=[order.id]),
        "delivery": get_delivery_json(order.delivery),
        "amount": f"{order.amount:.2f}",
        "is_open": order.is_open,
    }


def get_order_detail_json(order):
    return {
        "url": SERVER_NAME + reverse("order-detail", args=[order.id]),
        "delivery": order.delivery.id,
        "items": [
            {
                "product": order_item.product.id,
                "product_name": order_item.product_name,
                "product_unit_price": f"{order_item.product_unit_price:.2f}",
                "quantity": order_item.quantity,
                "amount": f"{order_item.amount:.2f}",
            }
            for order_item in order.items.all()
        ],
        "amount": f"{order.amount:.2f}",
        "message": order.message,
        "is_open": order.is_open,
    }


class TestDeliveryAPI(APITestCase):
    url_list = reverse_lazy("delivery-list")

    def test_list(self):
        """Check that authenticated user can retrieve list of opened deliveries. Deliveries must be ordered by date"""

        user = create_user()
        opened_deliveries = [create_opened_delivery() for _ in range(2)]
        create_closed_delivery()

        self.client.force_authenticate(user=user)
        response = self.client.get(self.url_list)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(), [get_delivery_json(d) for d in opened_deliveries]
        )

    def test_list_not_authenticated(self):
        response = self.client.get(self.url_list)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve(self):
        """Check that an opened Delivery can be retrieved.
        Also check that only delivery products are returned (not all products from producer)
        """

        user = create_user()
        # 3 producers, each one with 2 products
        producers = [create_producer() for _ in range(3)]
        [create_product(producer=p) for _ in range(2) for p in producers]

        delivery = create_opened_delivery(
            products=list(producers[0].products.all()) + [producers[1].products.last()]
        )

        self.client.force_authenticate(user=user)
        response = self.client.get(reverse("delivery-detail", args=[delivery.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), get_delivery_detail_json(delivery))

    def test_retrieve_not_authenticated(self):
        delivery = create_opened_delivery()
        response = self.client.get(reverse("delivery-detail", args=[delivery.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestOrderAPI(APITestCase):
    url_list = reverse_lazy("order-list")

    def _create_opened_and_closed_orders(self):
        product = create_product()
        self.orders = []
        for _ in range(3):
            self.orders.extend(
                (
                    create_order_item(
                        delivery=create_opened_delivery([product]),
                        product=product,
                        user=self.user,
                    ).order,
                    create_order_item(
                        delivery=create_closed_delivery([product]),
                        product=product,
                        user=self.user,
                    ).order,
                )
            )

    def test_list(self):
        self.user = create_user()
        self._create_opened_and_closed_orders()

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url_list)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            [
                get_order_json(o)
                for o in sorted(
                    self.orders, key=lambda x: x.delivery.date, reverse=True
                )
            ],
        )

    def test_list_not_authenticated(self):
        response = self.client.get(self.url_list)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create(self):
        user = create_user()
        products = [create_product() for _ in range(2)]
        delivery = create_opened_delivery(products=products)
        message = "New order"

        self.client.force_authenticate(user=user)
        payload = {
            "delivery": delivery.id,
            "items": [
                {"product": products[0].id, "quantity": 1},
                {"product": products[1].id, "quantity": 2},
            ],
            "message": message,
        }
        response = self.client.post(
            self.url_list, data=json.dumps(payload), content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(user.orders.count(), 1)
        new_order = user.orders.last()
        self.assertEqual(
            response.json()["url"],
            SERVER_NAME + reverse("order-detail", args=[new_order.id]),
        )
        expected_amount = products[0].unit_price + 2 * products[1].unit_price
        self.assertEqual(response.json()["amount"], f"{expected_amount:.2f}")
        self.assertTrue(response.json()["is_open"], expected_amount)

        self.assertEqual(new_order.delivery, delivery)
        self.assertEqual(new_order.amount, expected_amount)
        self.assertEqual(new_order.message, message)
        self.assertEqual(new_order.items.count(), 2)

    def test_create_not_authenticated(self):
        orders_count_initial = Order.objects.count()

        response = self.client.post(
            self.url_list,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Order.objects.count(), orders_count_initial)

    def test_create_invalid_delivery(self):
        user = create_user()
        assert not user.orders.count()
        self.client.force_authenticate(user=user)

        assert not Delivery.objects.count()
        response = self.client.post(
            self.url_list,
            data=json.dumps(
                {
                    "delivery": 1,  # non-existing delivery
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "delivery", response.json()
        )  # An error is returned for "delivery" field
        self.assertEqual(user.orders.count(), 0)

    def test_create_deadline_passed(self):
        user = create_user()
        product = create_product()
        delivery = create_closed_delivery(products=[product])

        self.client.force_authenticate(user=user)
        payload = {
            "delivery": delivery.id,
            "items": [{"product_id": product.id, "quantity": 1}],
        }
        response = self.client.post(
            self.url_list,
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("delivery", response.json())
        self.assertEqual(user.orders.count(), 0)

    def test_create_second_order_for_delivery(self):
        user = create_user()
        product = create_product()
        delivery = create_opened_delivery(products=[product])
        create_order_item(delivery=delivery, product=product, user=user)
        assert user.orders.count() == 1

        self.client.force_authenticate(user=user)
        payload = {
            "delivery": delivery.id,
            "items": [
                {
                    "product": product.id,
                    "quantity": 1,
                }
            ],
        }
        response = self.client.post(
            self.url_list, data=json.dumps(payload), content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("delivery", response.json())
        self.assertEqual(user.orders.count(), 1)

    def test_create_no_item(self):
        user = create_user()
        self.client.force_authenticate(user=create_user())

        payload = {
            "delivery": create_opened_delivery().id,
            "items": [],
        }
        response = self.client.post(
            self.url_list, data=json.dumps(payload), content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("items", response.json())
        self.assertEqual(user.orders.count(), 0)

    def test_create_product_not_in_delivery(self):
        user = create_user()
        products = [create_product() for _ in range(2)]
        delivery = create_opened_delivery(products=[products[0]])

        self.client.force_authenticate(user=user)
        payload = {
            "delivery": delivery.id,
            "items": [
                {"product": products[1].id, "quantity": 1},
            ],
        }
        response = self.client.post(
            self.url_list, data=json.dumps(payload), content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("items", response.json())
        self.assertEqual(user.orders.count(), 0)

    def test_retrieve(self):
        """Check that user can retrieve its orders (opened and closed)"""

        user = create_user()
        opened_order = create_order_item(
            delivery=create_opened_delivery(), user=user
        ).order
        # closed order with 2 items
        products = [create_product() for _ in range(2)]
        closed_order = user.orders.create(
            delivery=create_closed_delivery(products=products)
        )
        closed_order.items.create(product=products[0], quantity=1)
        closed_order.items.create(product=products[1], quantity=2)

        self.client.force_authenticate(user=user)
        for order in [opened_order, closed_order]:
            response = self.client.get(reverse("order-detail", args=[order.id]))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json(), get_order_detail_json(order))

    def test_retrieve_invalid_user(self):
        user1 = create_user()
        user2 = create_user()
        create_order_item(delivery=create_closed_delivery(), user=user2)

        self.client.force_authenticate(user=user1)
        response = self.client.get(
            reverse("order-detail", args=[user2.orders.last().id])
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_not_authenticated(self):
        order = create_order_item(create_closed_delivery()).order

        response = self.client.get(reverse("order-detail", args=[order.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update(self):
        user = create_user()
        products = [create_product() for _ in range(2)]
        opened_delivery = create_opened_delivery(products=products)
        opened_order = user.orders.create(
            delivery=opened_delivery, message="original order"
        )
        opened_order.items.create(product=products[0], quantity=1)
        opened_order.items.create(product=products[1], quantity=2)

        self.client.force_authenticate(user=user)
        payload = {
            "delivery": opened_delivery.id,
            "items": [{"product": products[1].id, "quantity": 3}],
            "message": "order updated",
        }
        response = self.client.put(
            reverse("order-detail", args=[opened_order.id]),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_amount = products[1].unit_price * 3
        self.assertEqual(response.json()["amount"], f"{new_amount:.2f}")

        updated_order = user.orders.last()  # note that id changes on update
        self.assertEqual(updated_order.amount, new_amount)
        self.assertEqual(updated_order.message, "order updated")
        self.assertEqual(updated_order.items.count(), 1)
        self.assertEqual(updated_order.items.first().product, products[1])
        self.assertEqual(updated_order.items.first().quantity, 3)

    def test_update_not_authenticated(self):
        order_item = create_order_item(delivery=create_opened_delivery())
        initial_quantity = order_item.quantity
        order = order_item.order

        payload = {
            "delivery": order.delivery.id,
            "items": [
                {"product": order_item.product.id, "quantity": initial_quantity + 1}
            ],
        }
        response = self.client.put(
            reverse("order-detail", args=[order.id]),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        order_item.refresh_from_db()
        self.assertEqual(order_item.quantity, initial_quantity)

    def test_update_deadline_passed(self):
        user = create_user()
        closed_delivery = create_closed_delivery()
        order_item = create_order_item(delivery=closed_delivery, user=user)
        initial_quantity = order_item.quantity

        self.client.force_authenticate(user=user)
        payload = {
            "delivery": closed_delivery.id,
            "items": [
                {
                    "product_id": order_item.product.id,
                    "quantity": initial_quantity + 1,
                }
            ],
        }
        response = self.client.put(
            reverse("order-detail", args=[order_item.order.id]),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("delivery", response.json())
        order_item.refresh_from_db()
        self.assertEqual(order_item.quantity, initial_quantity)

    def test_update_invalid_product(self):
        user = create_user()
        opened_delivery = create_opened_delivery()
        order_item = create_order_item(delivery=opened_delivery, user=user)
        initial_product = order_item.product
        initial_quantity = order_item.quantity

        self.client.force_authenticate(user=user)
        invalid_product_id = Product.objects.all().aggregate(Max("id"))["id__max"] + 1
        payload = {
            "delivery": opened_delivery.id,
            "items": [
                {"product": invalid_product_id, "quantity": initial_quantity + 1}
            ],
        }
        response = self.client.put(
            reverse("order-detail", args=[order_item.order.id]),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("items", response.json())
        order = user.orders.last()
        self.assertEqual(order.items.first().product, initial_product)
        self.assertEqual(order.items.first().quantity, initial_quantity)

    def test_delete(self):
        user = create_user()
        products = [create_product() for _ in range(2)]
        opened_order = Order.objects.create(
            user=user, delivery=create_opened_delivery(products=products)
        )
        item1 = opened_order.items.create(product=products[0], quantity=1)
        item2 = opened_order.items.create(product=products[1], quantity=2)

        self.client.force_authenticate(user=user)
        response = self.client.delete(reverse("order-detail", args=[opened_order.id]))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertNotIn(opened_order, user.orders.all())
        self.assertNotIn(item1, OrderItem.objects.all())
        self.assertNotIn(item2, OrderItem.objects.all())

    def test_delete_not_authenticated(self):
        order = create_order_item(delivery=create_opened_delivery()).order

        response = self.client.delete(reverse("order-detail", args=[order.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn(order, Order.objects.all())

    def test_delete_deadline_passed(self):
        user = create_user()
        closed_order = Order.objects.create(
            user=user, delivery=create_closed_delivery()
        )

        self.client.force_authenticate(user=user)
        response = self.client.delete(reverse("order-detail", args=[closed_order.id]))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(closed_order, user.orders.all())
