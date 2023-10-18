from django.test import TestCase
from django.urls import reverse

from baskets.tests.common import (
    create_closed_delivery,
    create_opened_delivery,
    create_order_item,
    create_user,
)


class WebPageTestCase(TestCase):
    def setUp(self):
        self.user = create_user()
        # deliveries
        self.closed_deliveries = [create_closed_delivery() for _ in range(4)]
        self.opened_deliveries = [create_opened_delivery() for _ in range(3)]
        # user orders
        self.closed_orders = [
            create_order_item(delivery=d, user=self.user).order
            for d in self.closed_deliveries[:2]
        ]
        create_order_item(delivery=self.opened_deliveries[0], user=self.user)
        # orders from other users
        create_order_item(delivery=self.closed_deliveries[0])
        create_order_item(delivery=self.opened_deliveries[0])

    def test_index_template(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("index"))
        self.assertTemplateUsed(response, "baskets/orders.html")

    def test_index_not_authenticated_redirects_to_login(self):
        response = self.client.get(reverse("index"))
        self.assertRedirects(response, "/accounts/login/?next=/")

    def test_index_opened_deliveries(self):
        """Check that 'index' page shows only opened deliveries (deadline not passed) in chronological order"""

        self.client.force_login(self.user)
        response = self.client.get(reverse("index"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(response.context["deliveries_orders"]), len(self.opened_deliveries)
        )
        shown_deliveries = [
            item["delivery"] for item in response.context["deliveries_orders"]
        ]
        self.assertEqual(
            shown_deliveries, sorted(self.opened_deliveries, key=lambda x: x.date)
        )

    def test_order_history_closed_deliveries(self):
        """Check that 'order history' page shows only closed user orders (deadline passed)
        in reverse chronological order"""

        self.client.force_login(self.user)
        response = self.client.get(reverse("order_history"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(response.context["deliveries_orders"]), len(self.closed_orders)
        )
        shown_orders = [item["order"] for item in response.context["deliveries_orders"]]
        self.assertEqual(
            shown_orders,
            sorted(self.closed_orders, key=lambda x: x.delivery.date, reverse=True),
        )
