from django.contrib.auth import get_user_model
from django.urls import reverse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select

from baskets.models import OrderItem, Order
from baskets.tests.common import (
    SeleniumTestCase,
    create_producer,
    create_product,
    create_order_item,
    create_opened_delivery,
    create_closed_delivery,
    create_user,
)


class TestAdmin(SeleniumTestCase):
    def setUp(self):
        super().setUp()

        # Admin login
        self.superuser = get_user_model().objects.create_superuser(username="admin")
        self.client.force_login(self.superuser)
        cookie = self.client.cookies["sessionid"]
        self.driver.get(self.live_server_url + reverse("admin:login"))
        self.driver.add_cookie({"name": "sessionid", "value": cookie.value})

    def _send_action(self, value):
        action_select = Select(self.driver.find_element(By.TAG_NAME, "select"))
        action_select.select_by_value(value)
        send_button = self.driver.find_element(By.CLASS_NAME, "button")
        send_button.click()


class TestProducer(TestAdmin):
    def test_product_deactivate(self):
        """Test that when a product is deactivated, related opened order_items are removed and a message is shown with a
        'mailto' link to contact concerned users"""

        producer = create_producer()
        product = create_product(producer)
        other_product = create_product()
        opened_delivery = create_opened_delivery([product, other_product])
        closed_delivery = create_closed_delivery([product])
        opened_order_item = create_order_item(delivery=opened_delivery, product=product)
        other_opened_order_item = create_order_item(
            delivery=opened_delivery, product=other_product
        )
        closed_order_item = create_order_item(delivery=closed_delivery, product=product)

        self.driver.get(
            self.live_server_url
            + reverse("admin:baskets_producer_change", args=[producer.id])
        )
        active_checkbox = self.driver.find_element(By.ID, "id_products-0-is_active")
        active_checkbox.click()
        save_button = self.driver.find_element(By.NAME, "_save")
        save_button.click()

        self.assertNotIn(opened_order_item, OrderItem.objects.all())
        self.assertIn(other_opened_order_item, OrderItem.objects.all())
        self.assertIn(closed_order_item, OrderItem.objects.all())

        message = self.driver.find_element(By.CLASS_NAME, "success")
        self.assertIn(
            f'<a href="mailto:?bcc={opened_order_item.order.user.email}">',
            message.get_attribute("innerHTML"),
        )


class TestDelivery(TestAdmin):
    def _select_delivery(self, delivery):
        delivery_url = reverse("admin:baskets_delivery_change", args=[delivery.id])
        checkbox = self.driver.find_element(
            By.XPATH, f"//a[@href='{delivery_url}']/../../td/input"
        )
        checkbox.click()

    def test_action_email_users(self):
        """Check that action 'mailto_users_from_deliveries' shows a message with a 'mailto' link"""

        deliveries = [create_opened_delivery() for _ in range(3)]
        orders = [
            Order.objects.create(user=create_user(), delivery=d) for d in deliveries
        ]
        users = [o.user for o in orders]

        self.driver.get(
            self.live_server_url + reverse("admin:baskets_delivery_changelist")
        )
        self._select_delivery(deliveries[0])
        self._select_delivery(deliveries[1])
        self._send_action("mailto_users_from_deliveries")

        message_html = self.driver.find_element(By.CLASS_NAME, "success").get_attribute(
            "innerHTML"
        )
        self.assertIn('<a href="mailto:', message_html)
        self.assertIn(users[0].email, message_html)
        self.assertIn(users[1].email, message_html)
        self.assertNotIn(users[2].email, message_html)

    def test_inactive_products_not_shown(self):
        delivery = create_opened_delivery()
        product = create_product()
        product.is_active = False
        product.save()
        create_product()  # another product (active)

        self.driver.get(
            self.live_server_url
            + reverse("admin:baskets_delivery_change", args=[delivery.id])
        )
        available_products_names = [
            option.text
            for option in self.driver.find_elements(
                By.CSS_SELECTOR, "#id_products_from option"
            )
        ]
        self.assertNotIn(product.name, available_products_names)
