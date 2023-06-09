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
    def test_product_remove(self):
        """Test that when a product is removed, related opened order_items are removed and a message is shown with a
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
        delete_checkbox = self.driver.find_element(By.CSS_SELECTOR, "[type='checkbox']")
        delete_checkbox.click()
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

    def test_soft_delete(self):
        """Check that when a producer is deleted, soft-delete is applied: producer is deactivated and not shown anymore
        on change list"""

        producer = create_producer()
        product = create_product(producer)

        self.driver.get(
            self.live_server_url + reverse("admin:baskets_producer_changelist")
        )
        producer_checkbox = self.driver.find_element(
            By.CSS_SELECTOR, "[type='checkbox']"
        )
        producer_checkbox.click()
        self._send_action("delete_selected")
        confirm_button = self.driver.find_element(
            By.CSS_SELECTOR, "input[type='submit']"
        )
        confirm_button.click()

        producer.refresh_from_db()
        self.assertFalse(producer.is_active)
        product.refresh_from_db()
        self.assertFalse(product.is_active)

        producers_count = self.driver.find_element(By.CSS_SELECTOR, ".paginator")
        self.assertIn("0", producers_count.text)


class TestDelivery(TestAdmin):
    def _check_delivery(self, delivery):
        delivery_url = reverse("admin:baskets_delivery_change", args=[delivery.id])
        checkbox = self.driver.find_element(
            By.XPATH, f"//a[@href='{delivery_url}']/../../td/input"
        )
        checkbox.click()

    def test_action_email_users(self):
        """Check that action 'mailto_users_from_deliveries' shows a message with a 'mailto' link"""

        delivery1 = create_opened_delivery()
        order1 = Order.objects.create(user=create_user(), delivery=delivery1)
        user1 = order1.user
        delivery2 = create_opened_delivery()
        order2 = Order.objects.create(user=create_user(), delivery=delivery2)
        user2 = order2.user
        delivery3 = create_opened_delivery()
        order3 = Order.objects.create(user=create_user(), delivery=delivery3)
        user3 = order3.user

        self.driver.get(
            self.live_server_url + reverse("admin:baskets_delivery_changelist")
        )
        self._check_delivery(delivery1)
        self._check_delivery(delivery2)
        self._send_action("mailto_users_from_deliveries")

        message_html = self.driver.find_element(By.CLASS_NAME, "success").get_attribute(
            "innerHTML"
        )
        self.assertIn('<a href="mailto:', message_html)
        self.assertIn(user1.email, message_html)
        self.assertIn(user2.email, message_html)
        self.assertNotIn(user3.email, message_html)
