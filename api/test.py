import json

from django.db.models import Max
from django.urls import reverse, reverse_lazy
from rest_framework import status

from baskets.models import Order, OrderItem, Product, Delivery
from baskets.tests.common import BasketsTestCase


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


def get_order_list_json(orders):
    return [
        {
            "url": SERVER_NAME + reverse("order-detail", args=[o.id]),
            "delivery": get_delivery_json(o.delivery),
            "amount": f"{o.amount:.2f}",
            "is_open": o.is_open,
        }
        for o in orders
    ]


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


class TestDeliveryAPI(BasketsTestCase):
    url_list = reverse_lazy("delivery-list")

    def test_list(self):
        """Check that list of opened deliveries can be retrieved through API. Deliveries must be ordered by date"""

        opened_deliveries = [self.d2, self.d3]
        expected_delivery_list_json = [get_delivery_json(d) for d in opened_deliveries]

        self.api_c.force_authenticate(user=self.u1)
        response = self.api_c.get(self.url_list)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), expected_delivery_list_json)

    def test_list_not_authenticated(self):
        response = self.api_c.get(self.url_list)

        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_detail(self):
        """Check that a Delivery can be retrieved through API. Also check that only delivery products are returned
        (not all products from producer)"""

        d2_expected_json = {
            "id": self.d2.id,
            "date": self.d2.date.isoformat(),
            "order_deadline": self.d2.order_deadline.isoformat(),
            "products_by_producer": [
                {
                    "name": "producer1",
                    "products": [get_product_json(self.product1)],
                },
                {
                    "name": "producer2",
                    "products": [get_product_json(self.product3)],
                },
            ],
            "message": self.d2.message,
        }

        self.api_c.force_authenticate(user=self.u1)
        response = self.api_c.get(reverse("delivery-detail", args=[self.d2.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), d2_expected_json)


class TestOrderAPI(BasketsTestCase):
    url_list = reverse_lazy("order-list")

    def test_list(self):
        """Check that user can get the list of all of its orders through API, ordered by reverse delivery date"""

        self.api_c.force_authenticate(user=self.u1)
        response = self.api_c.get(self.url_list)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), get_order_list_json([self.o2, self.o1]))

    def test_list_not_authenticated(self):
        """Check that a non-authenticated user gets an 'Unauthorized' or 'Forbidden' error
        (depending on authentication method) when trying to get order list through API
        """

        response = self.api_c.get(self.url_list)

        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_create(self):
        """Check that user can create an order through API"""

        self.api_c.force_authenticate(user=self.u1)
        user1_orders_count_initial = self.u1.orders.count()

        order_json = {
            "delivery": self.d3.id,
            "items": [
                {"product": self.product2.id, "quantity": 1},
                {"product": self.product3.id, "quantity": 2},
            ],
            "message": "New order",
        }
        response = self.api_c.post(
            self.url_list, data=json.dumps(order_json), content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(float(response.json()["amount"]), 3.30)
        self.assertEqual(
            response.json()["url"],
            SERVER_NAME + reverse("order-detail", args=[Order.objects.last().id]),
        )

        self.assertEqual(self.u1.orders.count(), user1_orders_count_initial + 1)

        new_order = Order.objects.last()
        self.assertEqual(new_order.delivery, self.d3)
        self.assertEqual(new_order.message, "New order")
        self.assertEqual(new_order.items.count(), 2)

    def test_create_not_authenticated(self):
        """Check that a non-authenticated user gets an "Unauthorized/Forbidden" error when trying to
        create order through API"""

        orders_count_initial = Order.objects.count()

        order_json = {
            "delivery": self.d2.id,
            "items": [{"product_id": self.product1.id, "quantity": 1}],
        }
        response = self.api_c.post(
            self.url_list,
            content_type="application/json",
        )

        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )
        self.assertEqual(Order.objects.count(), orders_count_initial)

    def test_create_invalid_delivery(self):
        """Check that when a user tries to create an order for a non-existing delivery:
        - 'Bad request' error is received
        - Order is not created"""

        self.api_c.force_authenticate(user=self.u2)
        u2_initial_orders_count = self.u2.orders.count()

        order_json = {
            "delivery": Delivery.objects.all().aggregate(Max("id"))["id__max"] + 1,
            "items": [{"product_id": self.product1.id, "quantity": 1}],
        }
        response = self.api_c.post(
            self.url_list,
            data=json.dumps(order_json),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "delivery", response.json()
        )  # An error is returned for "delivery" field
        self.assertEqual(self.u2.orders.count(), u2_initial_orders_count)

    def test_create_deadline_passed(self):
        """Check that when a user tries to create an order for a delivery which deadline is passed:
        - A 'Bad request' error is received
        - Order is not created"""

        self.api_c.force_authenticate(user=self.u2)
        u2_initial_orders_count = self.u2.orders.count()

        order_json = {
            "delivery": self.d1.id,
            "items": [{"product_id": self.product1.id, "quantity": 1}],
        }
        response = self.api_c.post(
            self.url_list,
            data=json.dumps(order_json),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("delivery", response.json())
        self.assertEqual(self.u2.orders.count(), u2_initial_orders_count)

    def test_create_second_order_for_delivery(self):
        """Check that user receives a 'Bad request' error when trying to create a second order for a given delivery"""

        self.api_c.force_authenticate(user=self.u2)
        user2_orders_count_initial = self.u2.orders.count()

        # user already has an order for d2
        order_json = {
            "delivery": self.d2.id,
            "items": [
                {
                    "product": self.product1.id,
                    "quantity": 1,
                }
            ],
        }
        response = self.api_c.post(
            self.url_list, data=json.dumps(order_json), content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("delivery", response.json())
        self.assertEqual(self.u2.orders.count(), user2_orders_count_initial)

    def test_create_no_item(self):
        """Check that user receives a 'bad request' error when trying to create an order without items"""

        self.api_c.force_authenticate(user=self.u1)
        user1_orders_count_initial = self.u1.orders.count()

        order_json = {
            "delivery": self.d3.id,
            "items": [],
        }
        response = self.api_c.post(
            self.url_list, data=json.dumps(order_json), content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("items", response.json())
        self.assertEqual(self.u1.orders.count(), user1_orders_count_initial)

    def test_create_product_not_in_delivery(self):
        """Check that user receives an error 400 when creating an order with a product not available in delivery"""

        self.api_c.force_authenticate(self.u1)
        user1_orders_count_initial = self.u1.orders.count()

        order_json = {
            "delivery": self.d3.id,
            "items": [
                {"product": self.product4.id, "quantity": 1},  # not available in d3
            ],
        }
        response = self.api_c.post(
            self.url_list, data=json.dumps(order_json), content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("items", response.json())
        self.assertEqual(self.u1.orders.count(), user1_orders_count_initial)

    def test_retrieve(self):
        """Check that user can retrieve its orders (opened and closed)"""

        opened_order = self.o2
        closed_order = self.o1

        self.api_c.force_authenticate(self.u1)
        for order in [opened_order, closed_order]:
            response = self.api_c.get(reverse("order-detail", args=[order.id]))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json(), get_order_detail_json(order))

    def test_retrieve_invalid_user(self):
        """Check that user1 gets a 'Not Found' error when trying to retrieve an user2 order"""

        self.api_c.force_authenticate(self.u1)
        response = self.api_c.get(
            reverse("order-detail", args=[self.u2.orders.last().id])
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_not_authenticated(self):
        response = self.api_c.get(reverse("order-detail", args=[self.o1.id]))

        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_update(self):
        """Check that user can update one of its orders through API"""

        self.api_c.force_authenticate(self.u1)

        original_order = self.o2
        updated_order_json = {
            "delivery": self.d3.id,
            "items": [{"product": self.product3.id, "quantity": 2}],
            "message": "order updated",
        }
        response = self.api_c.put(
            reverse("order-detail", args=[original_order.id]),
            data=json.dumps(updated_order_json),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(float(response.json()["amount"]), 2.30)

        updated_order = self.u1.orders.last()  # note that id changes on update
        self.assertEqual(updated_order.delivery, self.d3)
        self.assertEqual(updated_order.message, "order updated")
        self.assertEqual(updated_order.items.count(), 1)
        self.assertEqual(updated_order.items.first().product, self.product3)
        self.assertEqual(updated_order.items.first().quantity, 2)

    def test_update_deadline_passed(self):
        """Check that when a user tries to update an order for a delivery which deadline is passed:
        - A 'Bad request' error is received
        - Order is not updated"""

        self.api_c.force_authenticate(self.u1)

        original_order = self.o1  # closed order
        self.assertEqual(original_order.items.count(), 2)
        oi1_initial_quantity = self.o1i1.quantity
        updated_order_json = {
            "delivery": original_order.delivery.id,
            "items": [
                {"product_id": self.product1.id, "quantity": oi1_initial_quantity + 1}
            ],
        }
        response = self.api_c.put(
            reverse("order-detail", args=[original_order.id]),
            data=json.dumps(updated_order_json),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("delivery", response.json())

        self.o1.refresh_from_db()
        self.o1i1.refresh_from_db()
        self.assertEqual(self.o1.items.count(), 2)
        self.assertEqual(self.o1i1.quantity, oi1_initial_quantity)

    def test_update_invalid_product(self):
        """Check that, when trying to update an opened order with a non-existing product:
        - A 'Bad request' error is received
        - Order is not updated"""

        self.api_c.force_authenticate(self.u1)

        order = self.o2
        invalid_product_id = Product.objects.all().aggregate(Max("id"))["id__max"] + 1
        updated_order_json = {
            "delivery": order.delivery.id,
            "items": [{"product": invalid_product_id, "quantity": 2}],
            "message": "try to update",
        }
        response = self.api_c.put(
            reverse("order-detail", args=[order.id]),
            data=json.dumps(updated_order_json),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("items", response.json())

        order.refresh_from_db()
        self.assertEqual(order.items.count(), 2)
        self.assertEqual(order.items.first().product, self.product1)
        self.assertEqual(order.items.first().quantity, 1)
        self.assertEqual(order.items.last().product, self.product3)
        self.assertEqual(order.items.last().quantity, 3)
        self.assertEqual(order.message, "order 2")

    def test_delete(self):
        """Check that user can delete one of its orders, including all of its items, through API"""

        self.api_c.force_authenticate(self.u1)

        response = self.api_c.delete(reverse("order-detail", args=[self.o2.id]))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertNotIn(self.o2, self.u1.orders.all())
        self.assertNotIn(self.o2i1, OrderItem.objects.all())
        self.assertNotIn(self.o2i2, OrderItem.objects.all())

    def test_delete_not_authenticated(self):
        """Check that a not authenticated user gets an "Unauthorized" error when trying to delete order through API"""

        response = self.api_c.delete(reverse("order-detail", args=[self.o1.id]))

        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )
        self.assertIn(self.o1, Order.objects.all())

    def test_delete_deadline_passed(self):
        user = create_user()
        closed_order = Order.objects.create(user=user, delivery=create_closed_delivery())

        self.client.force_authenticate(user=user)
        response = self.client.delete(reverse("order-detail", args=[closed_order.id]))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(closed_order, user.orders.all())
