from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from selenium import webdriver

from baskets.models import Producer
from baskets.tests.pageobjects import LoginPage
from baskets.tests.setup import BasketsTestCase


class FunctionalTestCase(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.driver = webdriver.Chrome()
        cls.driver.maximize_window()
        cls.driver.implicitly_wait(10)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()

    def setUp(self):
        BasketsTestCase.setUp(self)

    def _login(self):
        login_page = LoginPage(self.driver, self.live_server_url)
        login_page.load()
        # Check that 'Login' page is correctly loaded
        self.assertEqual(self.driver.current_url, self.live_server_url + login_page.url)
        self.assertEqual(login_page.title, "Connexion")

        login_page.set_email("user1@baskets.com")
        login_page.set_password("secret")
        next_orders_page = login_page.submit()
        # Check that 'Next orders' page is correctly loaded and user1 is logged-in
        self.assertEqual(self.driver.current_url, self.live_server_url + reverse("baskets:index"))
        self.assertEqual(next_orders_page.title, "Commandes à venir")
        self.assertEqual(next_orders_page.username, "user1")
        return next_orders_page

    def _check_producers(self, next_orders_page, delivery):
        """Check order-view producers: count, name and products. Check that we only show producers that have products
         available on delivery."""
        producers_to_show = Producer.objects.filter(products__in=delivery.products.all()).distinct()

        self.assertEqual(next_orders_page.get_producers_count(), producers_to_show.count())
        for producer_index, producer in enumerate(producers_to_show):
            self.assertEqual(next_orders_page.get_producer_name(producer_index), producer.name)
            # check that items are listed under corresponding producer
            for item_index in range(next_orders_page.get_producer_items_count(producer_index)):
                item_name = next_orders_page.get_item_name(item_index, producer_index)
                self.assertTrue(producer.products.filter(name=item_name))

    def _check_producer_badge(self, next_orders_page, producer_index):
        """Check that producer badge value matches the sum of producer items quantities"""
        quantity_sum = sum(
            next_orders_page.get_item_quantity(item_index, producer_index)
            for item_index in range(next_orders_page.get_producer_items_count(producer_index))
        )
        self.assertEqual(quantity_sum, next_orders_page.get_producer_badge_value(producer_index))

    def _check_order_view_items(self, next_orders_page, delivery):
        """Check that order view items match delivery products"""
        delivery_products = delivery.products.all()

        # Check available products count
        items_count = next_orders_page.get_items_count()
        self.assertEqual(items_count, len(delivery_products))

        # Check products name, unit price
        for index in range(items_count):
            self.assertEqual(next_orders_page.get_item_name(index), delivery_products[index].name)
            self.assertEqual(next_orders_page.get_item_unit_price(index), delivery_products[index].unit_price)

    def _update_item_quantity(self, next_orders_page, item_index, item_quantity):
        """set item quantity and check updated item amount"""
        self.assertTrue(next_orders_page.item_quantity_is_writable(item_index))
        item_unit_price = next_orders_page.get_item_unit_price(item_index)
        expected_item_amount = item_quantity * item_unit_price

        next_orders_page.set_item_quantity(item_index, item_quantity)
        self.assertEqual(next_orders_page.get_item_amount(item_index), expected_item_amount)

    def test_create_order(self):
        next_orders_page = self._login()
        delivery_index = 1  # self.d3
        # Check that delivery has no order
        self.assertIsNone(next_orders_page.get_order_url(delivery_index))
        self.assertIsNone(next_orders_page.get_order_amount(delivery_index))

        next_orders_page.open_order(delivery_index)
        self.assertIn(next_orders_page.get_delivery_date(delivery_index), next_orders_page.get_order_view_title())
        next_orders_page.open_all_producers()
        self._check_producers(next_orders_page=next_orders_page, delivery=self.d3)
        self._check_order_view_items(next_orders_page=next_orders_page, delivery=self.d3)
        # check order and items initial amounts
        self.assertEqual(next_orders_page.get_order_view_amount(), 0.00)
        for index in range(next_orders_page.get_items_count()):
            self.assertEqual(next_orders_page.get_item_amount(index), 0.00)

        # add all items to order and check total order amount
        expected_order_amount = next_orders_page.get_order_view_amount()
        for index in range(next_orders_page.get_items_count()):
            self._update_item_quantity(next_orders_page=next_orders_page, item_index=index, item_quantity=index+1)
            expected_order_amount += next_orders_page.get_item_amount(index)
        self.assertEqual(next_orders_page.get_order_view_amount(), expected_order_amount)

        # check badges
        for producer_index in range(next_orders_page.get_producers_count()):
            self._check_producer_badge(next_orders_page, producer_index)

        # Save order and check that order list is updated
        next_orders_page.save_order()
        self.assertIsNotNone(next_orders_page.get_order_url(delivery_index))
        self.assertEqual(next_orders_page.get_order_amount(delivery_index), expected_order_amount)

        # Check that order has been created in database
        self.assertEqual(self.u1.orders.last().amount, expected_order_amount)

    def test_update_order(self):
        next_orders_page = self._login()
        delivery_index = 0  # self.d2
        next_orders_page.open_order(delivery_index)
        next_orders_page.open_all_producers()

        item_index = 0
        initial_item_quantity = next_orders_page.get_item_quantity(item_index)
        initial_order_view_amount = next_orders_page.get_order_view_amount()

        new_quantity = initial_item_quantity + 1
        self._update_item_quantity(next_orders_page=next_orders_page, item_index=item_index, item_quantity=new_quantity)
        expected_order_amount = initial_order_view_amount + next_orders_page.get_item_unit_price(item_index)
        self.assertEqual(next_orders_page.get_order_view_amount(), expected_order_amount)

        # Save order and check that it has been correctly updated in order list and database
        next_orders_page.save_order()
        self.assertEqual(next_orders_page.get_order_amount(delivery_index), expected_order_amount)
        self.assertEqual(self.u1.orders.last().amount, expected_order_amount)

    def test_delete_order(self):
        next_orders_page = self._login()
        delivery_index = 0  # self.d2
        next_orders_page.open_order(delivery_index)

        next_orders_page.delete_order()
        self.assertIsNone(next_orders_page.get_order_url(delivery_index))
        self.assertIsNone(next_orders_page.get_order_amount(delivery_index))

    def test_view_closed_order(self):
        next_orders_page = self._login()
        history_page = next_orders_page.load_history_page()
        self.assertEqual(history_page.title, "Historique")

        delivery_index = 0  # self.d1
        self.assertEqual(history_page.get_order_amount(delivery_index), self.o1.amount)

        history_page.open_order(delivery_index)
        self.assertIn(history_page.get_delivery_date(delivery_index), history_page.get_order_view_title())
        self.assertEqual(history_page.get_order_amount(delivery_index), history_page.get_order_view_amount())
        self.assertEqual(history_page.get_items_count(), self.o1.items.count())
        for index, item in enumerate(self.o1.items.all()):
            self.assertEqual(history_page.get_item_unit_price(index), item.saved_p_unit_price)
            self.assertEqual(history_page.get_item_name(index), item.saved_p_name)
            self.assertEqual(history_page.get_item_quantity(index), item.quantity)
            self.assertEqual(history_page.get_item_amount(index), item.amount)
