from baskets.tests.common import BasketsTestCase

from django.urls import reverse


class WebPageTestCase(BasketsTestCase):
    def test_index_template(self):
        self.c.force_login(self.u1)
        response = self.c.get(reverse("index"))
        self.assertTemplateUsed(response, "baskets/orders.html")

    def test_index_not_authenticated_redirects_to_login(self):
        response = self.c.get(reverse("index"))
        self.assertRedirects(response, "/accounts/login/?next=/")

    def test_index_opened_deliveries(self):
        """Check that 'index' page contains only opened deliveries (deadline not passed) in chronological order"""

        self.c.force_login(self.u1)
        response = self.c.get(reverse("index"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["deliveries_orders"]), 2)
        self.assertEqual(response.context["deliveries_orders"][0]["delivery"], self.d2)
        self.assertEqual(response.context["deliveries_orders"][1]["delivery"], self.d3)

    def test_order_history_closed_deliveries(self):
        """Check that 'order history' page contains only closed deliveries (deadline passed)"""

        self.c.force_login(self.u1)
        response = self.c.get(reverse("order_history"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["deliveries_orders"]), 1)
        self.assertEqual(response.context["deliveries_orders"][0]["delivery"], self.d1)
