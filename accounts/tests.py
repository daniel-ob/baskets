from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


class AccountsTest(TestCase):
    def test_profile_page_shows_user_info(self):
        user = get_user_model().objects.create_user(
            username="user1",
            first_name="test",
            last_name="user",
            email="user1@baskets.com",
            phone="0123456789",
            address="my street, my city",
            password="secret",
        )

        c = Client()
        c.force_login(user)
        response = c.get(reverse("profile"))

        self.assertEqual(response.status_code, 200)

        initial_form_data = response.context["form"].initial
        self.assertEqual(initial_form_data["email"], user.email)
        self.assertEqual(initial_form_data["first_name"], user.first_name)
        self.assertEqual(initial_form_data["last_name"], user.last_name)
        self.assertEqual(initial_form_data["phone"], user.phone)
        self.assertEqual(initial_form_data["address"], user.address)
