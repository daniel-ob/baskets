from datetime import date, timedelta
import json

from django.db.models import Max

from baskets.models import Order, OrderItem, Product
from baskets.tests.setup import BasketsTestCase


class APITestCase(BasketsTestCase):
    def test_order_list_get(self):
        """Check that user can get the list of all of its orders through API, ordered by reverse delivery date"""

        # log-in user1
        self.c.force_login(self.u1)

        user_order_list_expected_json = [
            {"id": self.o2.id, "delivery_id": self.o2.delivery.id},
            {"id": self.o1.id, "delivery_id": self.o1.delivery.id},
        ]

        response = self.c.get("/orders")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), user_order_list_expected_json)

    def test_order_list_get_not_authenticated(self):
        """Check that a non-authenticated user gets an "Unauthorized" error when trying to get order list through API"""

        response = self.c.get("/orders")

        self.assertEqual(response.status_code, 401)

    def test_order_creation(self):
        """Check that user can create an order through API"""

        self.c.force_login(self.u1)

        user1_orders_count_initial = self.u1.orders.count()

        order_json = {
            "delivery_id": self.d3.id,
            "items": [
                {"product_id": self.product2.id, "quantity": 1},
                {"product_id": self.product3.id, "quantity": 2},
            ],
            "message": "New order",
        }
        response = self.c.post(
            "/orders", data=json.dumps(order_json), content_type="application/json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(float(response.json()["amount"]), 3.30)
        self.assertEqual(response.json()["url"], f"/orders/{Order.objects.last().id}")

        self.assertEqual(self.u1.orders.count(), user1_orders_count_initial + 1)

        new_order = Order.objects.last()
        self.assertEqual(new_order.delivery, self.d3)
        self.assertEqual(new_order.message, "New order")
        self.assertEqual(new_order.items.count(), 2)

    def test_order_creation_not_authenticated(self):
        """Check that a non-authenticated user gets an "Unauthorized" error when trying to create order through API"""

        orders_count_initial = Order.objects.count()

        order_json = {
            "delivery_id": self.d2.id,
            "items": [{"product_id": self.product1.id, "quantity": 1}],
        }
        response = self.c.post(
            "/orders", data=json.dumps(order_json), content_type="application/json"
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(Order.objects.count(), orders_count_initial)

    def test_order_creation_deadline_passed(self):
        """Check that when a user tries to create an order for a delivery which deadline is passed:
        - A 'Bad request' error is received
        - Order is not created"""

        self.c.force_login(self.u2)
        u2_initial_orders_count = self.u2.orders.count()

        order_json = {
            "delivery_id": self.d1.id,
            "items": [{"product_id": self.product1.id, "quantity": 1}],
        }
        response = self.c.post(
            "/orders", data=json.dumps(order_json), content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.u2.orders.count(), u2_initial_orders_count)

    def test_order_creation_second_order_for_delivery(self):
        """Check that user receives a 'Bad request' error when trying to create a second order for a given delivery"""

        self.c.force_login(self.u2)
        user2_orders_count_initial = self.u2.orders.count()

        # user already has an order for d2
        order_json = {"delivery_id": self.d2.id}
        response = self.c.post(
            "/orders", data=json.dumps(order_json), content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.u2.orders.count(), user2_orders_count_initial)

    def test_order_creation_no_item(self):
        """Check that user receives a 'bad request' error when trying to create an order without items"""

        self.c.force_login(self.u1)
        user1_orders_count_initial = self.u1.orders.count()

        order_json = {
            "delivery_id": self.d2.id,
        }
        response = self.c.post(
            "/orders", data=json.dumps(order_json), content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.u1.orders.count(), user1_orders_count_initial)

    def test_order_creation_invalid_product(self):
        """Check that user receives an error 400 when creating an order with a product not available in delivery"""

        self.c.force_login(self.u1)
        user1_orders_count_initial = self.u1.orders.count()

        # product2 is not available in d2
        order_json = {
            "delivery_id": self.d2.id,
            "items": [
                {"product_id": self.product1.id, "quantity": 1},
                {"product_id": self.product2.id, "quantity": 1},
            ],
        }
        response = self.c.post(
            "/orders", data=json.dumps(order_json), content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.u1.orders.count(), user1_orders_count_initial)

    def test_opened_order_get(self):
        """Check that user can retrieve one of its opened orders"""

        self.c.force_login(self.u1)

        o2_expected_json = {
            "delivery_id": self.d2.id,
            "items": [
                {
                    "product": {
                        "id": self.product1.id,
                        "name": "product1",
                        "unit_price": "0.50",
                    },
                    "quantity": 1,
                    "amount": "0.50",
                },
                {
                    "product": {
                        "id": self.product3.id,
                        "name": "product3",
                        "unit_price": "1.15",
                    },
                    "quantity": 3,
                    "amount": "3.45",
                },
            ],
            "amount": "3.95",
            "message": "order 2",
            "is_open": True,
        }

        response = self.c.get(f"/orders/{self.o2.id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), o2_expected_json)

    def test_closed_order_get(self):
        """Check that user can retrieve one of its closed orders"""

        self.c.force_login(self.u1)

        self.product1.unit_price = 1.00
        self.product1.name = "product1 (updated)"
        self.product1.save()

        # product1 updates must not affect closed order items
        o1_expected_json = {
            "delivery_id": self.d1.id,
            "items": [
                {
                    "product": {"name": "product1", "unit_price": "0.50"},
                    "quantity": 4,
                    "amount": "2.00",
                },
                {
                    "product": {"name": "product2", "unit_price": "1.00"},
                    "quantity": 1,
                    "amount": "1.00",
                },
            ],
            "amount": "3.00",
            "message": "order 1",
            "is_open": False,
        }

        response = self.c.get(f"/orders/{self.o1.id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), o1_expected_json)

    def test_order_get_invalid_user(self):
        """Check that user1 gets a 'Forbidden' error when trying to retrieve an user2 order"""

        self.c.force_login(self.u1)
        response = self.c.get(f"/orders/{self.u2.orders.last().id}")
        self.assertEqual(response.status_code, 403)

    def test_order_update(self):
        """Check that user can update one of its orders through API"""

        # log-in user1
        self.c.force_login(self.u1)

        updated_order_json = {
            "items": [{"product_id": self.product3.id, "quantity": 2}],
            "message": "order updated",
        }
        response = self.c.put(
            f"/orders/{self.o2.id}",
            data=json.dumps(updated_order_json),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(float(response.json()["amount"]), 2.30)

        self.o2.refresh_from_db()
        self.assertEqual(self.o2.message, "order updated")
        self.assertEqual(self.o2.items.count(), 1)

    def test_order_update_deadline_passed(self):
        """Check that when a user tries to update an order for a delivery which deadline is passed:
        - A 'Bad request' error is received
        - Order is not updated"""

        self.c.force_login(self.u1)

        self.assertEqual(self.o1.items.count(), 2)
        oi1_initial_quantity = self.o1i1.quantity
        oi1_new_quantity = oi1_initial_quantity - 1
        updated_order_json = {
            "items": [{"product_id": self.product1.id, "quantity": oi1_new_quantity}],
            "message": "order updated",
        }
        response = self.c.put(
            f"/orders/{self.o1.id}",
            data=json.dumps(updated_order_json),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.o1.refresh_from_db()
        self.o1i1.refresh_from_db()
        self.assertEqual(self.o1.items.count(), 2)
        self.assertEqual(self.o1i1.quantity, oi1_initial_quantity)

    def test_order_update_invalid_product(self):
        """Check that, when trying to update an opened order with a non-existing product:
        - A 'Not found' error is received
        - Order is not updated"""

        # log-in user1
        self.c.force_login(self.u1)

        invalid_product_id = Product.objects.all().aggregate(Max("id"))["id__max"] + 1
        updated_order_json = {
            "items": [{"product_id": invalid_product_id, "quantity": 2}],
            "message": "try to update",
        }
        response = self.c.put(
            f"/orders/{self.o2.id}",
            data=json.dumps(updated_order_json),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)
        self.o2.refresh_from_db()
        self.assertEqual(self.o2.items.count(), 2)
        self.assertEqual(self.o2.items.first().product.id, self.product1.id)
        self.assertEqual(self.o2.items.first().quantity, 1)
        self.assertEqual(self.o2.items.last().product.id, self.product3.id)
        self.assertEqual(self.o2.items.last().quantity, 3)
        self.assertEqual(self.o2.message, "order 2")

    def test_order_delete(self):
        """Check that user can delete one of its orders, including all of its items, through API"""

        self.c.force_login(self.u1)

        response = self.c.delete(f"/orders/{self.o2.id}")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.o2, self.u1.orders.all())
        self.assertNotIn(self.o2i1, OrderItem.objects.all())
        self.assertNotIn(self.o2i2, OrderItem.objects.all())

    def test_order_delete_not_authenticated(self):
        """Check that a not authenticated user gets an "Unauthorized" error when trying to delete order through API"""

        response = self.c.delete(
            f"/orders/{self.o1.id}",
        )

        self.assertEqual(response.status_code, 401)
        self.assertIn(self.o1, Order.objects.all())

    def test_delivery_list_get(self):
        """Check that next opened deliveries list can be retrieved through API. Deliveries must be ordered by date"""

        deliveries_list_expected_json = [
            {"id": self.d2.id, "date": self.d2.date.isoformat()},
            {"id": self.d3.id, "date": self.d3.date.isoformat()},
        ]
        response = self.c.get("/deliveries")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), deliveries_list_expected_json)

    def test_delivery_get(self):
        """Check that a delivery can be retrieved through API"""

        today = date.today()
        tomorrow = today + timedelta(days=1)
        d2_expected_json = {
            "date": tomorrow.isoformat(),
            "order_deadline": today.isoformat(),
            "products_by_producer": [
                {
                    "id": self.producer1.id,
                    "name": "producer1",
                    "products": [
                        {
                            "id": self.product1.id,
                            "name": "product1",
                            "unit_price": "0.50",
                        },
                    ],
                },
                {
                    "id": self.producer2.id,
                    "name": "producer2",
                    "products": [
                        {
                            "id": self.product3.id,
                            "name": "product3",
                            "unit_price": "1.15",
                        }
                    ],
                },
            ],
            "message": "delivery 2",
            "is_open": True,
        }

        response = self.c.get(f"/deliveries/{self.d2.id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), d2_expected_json)
