from allauth.account.models import EmailAddress
from django.contrib.auth import get_user, get_user_model
from django.test import TestCase
from django.urls import reverse


class AccountsTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="test_user",
            email="test_user@baskets.com",
            password="secret",
        )
        # verify user email address, so he can log in
        EmailAddress.objects.create(
            user=self.user, email=self.user.email, verified=True
        )

    def test_register_template(self):
        response = self.client.get(reverse("account_signup"))
        self.assertTemplateUsed(response, "account/signup.html")

    def test_login_template(self):
        response = self.client.get(reverse("account_login"))
        self.assertTemplateUsed(response, "account/login.html")

    def test_password_reset_template(self):
        response = self.client.get(reverse("account_reset_password"))
        self.assertTemplateUsed(response, "account/password_reset.html")

    def test_login(self):
        response = self.client.post(
            reverse("account_login"),
            {"login": self.user.email, "password": "secret"},
        )
        self.assertRedirects(response, reverse("index"))
        user = get_user(self.client)
        self.assertTrue(user.is_authenticated)
        self.assertEqual(user.username, self.user.username)

    def test_logout_redirects_to_login(self):
        response = self.client.get(reverse("account_logout"))
        self.assertRedirects(response, "/accounts/login/")


class ProfileTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="user1",
            first_name="test",
            last_name="user",
            email="user1@baskets.com",
            phone="0123456789",
            address="my street, my city",
            password="secret",
        )

    def test_shows_user_data(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("profile"))

        self.assertEqual(response.status_code, 200)
        initial_form_data = response.context["form"].initial
        self.assertEqual(initial_form_data["email"], self.user.email)
        self.assertEqual(initial_form_data["first_name"], self.user.first_name)
        self.assertEqual(initial_form_data["last_name"], self.user.last_name)
        self.assertEqual(initial_form_data["phone"], self.user.phone)
        self.assertEqual(initial_form_data["address"], self.user.address)

    def test_update(self):
        updated_user_data = {
            "email": "test_user@baskets.com",
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
            "phone": "0123454321",  # must be compliant with FR_PHONE_REGEX
            "address": "another street, same city",
        }

        self.client.force_login(self.user)
        response = self.client.post(reverse("profile"), data=updated_user_data)

        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, updated_user_data["email"])
        self.assertEqual(self.user.phone, updated_user_data["phone"])
        self.assertEqual(self.user.address, updated_user_data["address"])
