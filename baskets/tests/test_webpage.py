from baskets.tests.setup import BasketsTestCase

from django.urls import reverse


class WebPageTestCase(BasketsTestCase):
    def test_index_template(self):
        self.c.force_login(self.u1)
        response = self.c.get(reverse("baskets:index"))
        self.assertTemplateUsed(response, "baskets/index.html")

    def test_index_not_authenticated_redirects_to_login(self):
        response = self.c.get(reverse("baskets:index"))
        self.assertRedirects(response, "/login/?next=/")

    def test_user_login(self):
        response = self.c.post(reverse("baskets:login"), {"username": "user1", "password": "secret"})
        self.assertRedirects(response, reverse("baskets:index"))
        # TODO: check that correct user is logged

    def test_index_opened_deliveries(self):
        """Check that 'index' page contains only opened deliveries (deadline not passed) in chronological order"""

        self.c.force_login(self.u1)
        response = self.c.get(reverse("baskets:index"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["deliveries_orders"]), 2)
        self.assertEqual(response.context["deliveries_orders"][0]["delivery"], self.d2)
        self.assertEqual(response.context["deliveries_orders"][1]["delivery"], self.d3)

    def test_order_history_closed_deliveries(self):
        """Check that 'order history' page contains only closed deliveries (deadline passed)"""

        self.c.force_login(self.u1)
        response = self.c.get(reverse("baskets:order_history"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["deliveries_orders"]), 1)
        self.assertEqual(response.context["deliveries_orders"][0]["delivery"], self.d1)

    def test_profile_page(self):
        """Check that 'profile' page shows user information"""

        self.c.force_login(self.u1)
        response = self.c.get(reverse("baskets:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"].initial["username"], self.u1.username)
        self.assertEqual(response.context["form"].initial["first_name"], self.u1.first_name)
        self.assertEqual(response.context["form"].initial["last_name"], self.u1.last_name)
        self.assertEqual(response.context["form"].initial["email"], self.u1.email)
        self.assertEqual(response.context["form"].initial["phone"], self.u1.phone)
        self.assertEqual(response.context["form"].initial["address"], self.u1.address)
