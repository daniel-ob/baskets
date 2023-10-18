from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.urls import reverse

from baskets.models import Order, Producer, Product
from baskets.tests.common import (
    SeleniumTestCase,
    create_closed_delivery,
    create_opened_delivery,
    create_order_item,
    create_producer,
    create_product,
)
from baskets.tests.pageobjects import LoginPage


class FunctionalTestCase(SeleniumTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="test_user",
            email="test_user@baskets.com",
            password="secret",
        )
        # verify user email address, so he can directly log in
        EmailAddress.objects.create(
            user=self.user, email=self.user.email, verified=True
        )

        producer = create_producer()
        self.products = [create_product(producer=producer) for _ in range(3)]
        self.products += [create_product() for _ in range(2)]
        self.opened_delivery1 = create_opened_delivery(products=self.products)
        self.opened_delivery2 = create_opened_delivery(products=self.products)
        assert self.opened_delivery2.date > self.opened_delivery1.date
        self.order1 = create_order_item(
            delivery=self.opened_delivery1, user=self.user
        ).order

    def _login(self):
        login_page = LoginPage(self.driver, self.live_server_url)
        login_page.load()
        self.assertEqual(self.driver.current_url, self.live_server_url + login_page.url)
        self.assertEqual(login_page.title, "Sign In")

        login_page.set_login(self.user.email)
        login_page.set_password("secret")
        next_orders_page = login_page.submit()
        self.assertEqual(
            self.driver.current_url, self.live_server_url + reverse("index")
        )
        self.assertEqual(next_orders_page.title, "Next orders")
        self.assertEqual(next_orders_page.username, self.user.username)

        return next_orders_page

    def _check_producers_and_products(self, next_orders_page, delivery):
        producers_to_show = (
            Producer.objects.filter(products__in=delivery.products.all())
            .distinct()
            .order_by("name")
        )
        self.assertEqual(
            next_orders_page.get_producers_count(), producers_to_show.count()
        )
        for producer_index, producer in enumerate(producers_to_show):
            self.assertEqual(
                next_orders_page.get_producer_name(producer_index), producer.name
            )
            producer_products_to_show = delivery.products.filter(
                producer=producer
            ).order_by("name")

            items_count = next_orders_page.get_producer_items_count(producer_index)
            self.assertEqual(items_count, producer_products_to_show.count())
            for item_index in range(items_count):
                item_id = next_orders_page.get_item_id(item_index, producer_index)
                product = Product.objects.get(id=item_id)
                self.assertEqual(
                    next_orders_page.get_item_name(item_index, producer_index),
                    product.name,
                )
                self.assertEqual(
                    next_orders_page.get_item_unit_price(item_index, producer_index),
                    product.unit_price,
                )

    def _check_producer_badges_values(self, next_orders_page):
        for producer_index in range(next_orders_page.get_producers_count()):
            quantity_sum = sum(
                next_orders_page.get_item_quantity(item_index, producer_index)
                for item_index in range(
                    next_orders_page.get_producer_items_count(producer_index)
                )
            )
            self.assertEqual(
                quantity_sum, next_orders_page.get_producer_badge_value(producer_index)
            )

    def _update_item_quantity_and_check_amount(
        self, next_orders_page, item_index, item_quantity
    ):
        assert next_orders_page.item_quantity_is_writable(item_index)
        item_unit_price = next_orders_page.get_item_unit_price(item_index)
        next_orders_page.set_item_quantity(item_index, item_quantity)
        self.assertEqual(
            next_orders_page.get_item_amount(item_index),
            item_quantity * item_unit_price,
        )

    def test_create_order(self):
        next_orders_page = self._login()
        self.assertEqual(next_orders_page.get_deliveries_count(), 2)
        # Deliveries must be sorted by date
        self.assertEqual(next_orders_page.get_delivery_id(0), self.opened_delivery1.id)
        self.assertEqual(next_orders_page.get_delivery_id(1), self.opened_delivery2.id)
        # Check orders
        self.assertIsNotNone(next_orders_page.get_order_url(0))
        self.assertEqual(next_orders_page.get_order_amount(0), self.order1.amount)
        self.assertIsNone(next_orders_page.get_order_url(1))
        self.assertIsNone(next_orders_page.get_order_amount(1))

        delivery_index = 1  # self.opened_delivery2
        next_orders_page.open_order(delivery_index)
        self.assertIn(
            next_orders_page.get_delivery_date(delivery_index),
            next_orders_page.get_order_view_title(),
        )
        next_orders_page.open_all_producers()
        self._check_producers_and_products(
            next_orders_page=next_orders_page, delivery=self.opened_delivery2
        )
        # check order and items initial amounts
        self.assertEqual(next_orders_page.get_order_view_amount(), 0.00)
        for index in range(next_orders_page.get_items_count()):
            self.assertEqual(next_orders_page.get_item_amount(index), 0.00)

        # add all items to order and check the total order amount
        expected_order_amount = 0
        for index in range(next_orders_page.get_items_count()):
            self._update_item_quantity_and_check_amount(
                next_orders_page=next_orders_page,
                item_index=index,
                item_quantity=index + 1,
            )
            expected_order_amount += next_orders_page.get_item_amount(index)
        self.assertEqual(
            next_orders_page.get_order_view_amount(), expected_order_amount
        )
        self._check_producer_badges_values(next_orders_page)

        next_orders_page.save_order()
        # Check that order is created in DB
        new_order = self.user.orders.last()
        self.assertEqual(new_order.delivery, self.opened_delivery2)
        self.assertEqual(new_order.amount, expected_order_amount)
        # Check that order-list is updated
        self.assertIsNotNone(next_orders_page.get_order_url(delivery_index))
        self.assertEqual(
            next_orders_page.get_order_amount(delivery_index), expected_order_amount
        )

    def test_update_order(self):
        next_orders_page = self._login()
        delivery_index = 0  # self.opened_delivery1
        next_orders_page.open_order(delivery_index)
        next_orders_page.open_all_producers()

        item_index = 0
        initial_item_quantity = next_orders_page.get_item_quantity(item_index)
        initial_order_view_amount = next_orders_page.get_order_view_amount()

        new_quantity = initial_item_quantity + 1
        self._update_item_quantity_and_check_amount(
            next_orders_page=next_orders_page,
            item_index=item_index,
            item_quantity=new_quantity,
        )
        expected_order_amount = (
            initial_order_view_amount + next_orders_page.get_item_unit_price(item_index)
        )
        self.assertEqual(
            next_orders_page.get_order_view_amount(), expected_order_amount
        )

        next_orders_page.save_order()
        # Check that it has been correctly updated in order-list and database
        self.assertEqual(
            next_orders_page.get_order_amount(delivery_index), expected_order_amount
        )
        self.assertEqual(self.user.orders.last().amount, expected_order_amount)

    def test_delete_order(self):
        next_orders_page = self._login()
        delivery_index = 0  # self.opened_delivery1
        assert next_orders_page.get_order_url(delivery_index) is not None
        next_orders_page.open_order(delivery_index)

        next_orders_page.delete_order()
        self.assertIsNone(next_orders_page.get_order_url(delivery_index))
        self.assertIsNone(next_orders_page.get_order_amount(delivery_index))

    def test_view_closed_order(self):
        closed_order1 = create_order_item(
            delivery=create_closed_delivery(), user=self.user
        ).order
        closed_order2 = Order.objects.create(
            delivery=create_closed_delivery(self.products), user=self.user
        )
        for idx, product in enumerate(closed_order2.delivery.products.all()):
            closed_order2.items.create(product=product, quantity=idx + 1)
        assert closed_order1.delivery.date > closed_order2.delivery.date

        # product price or name update must not affect closed order amount
        product = closed_order1.items.first().product
        product.unit_price += 1
        product.name += "(updated)"
        product.save()

        next_orders_page = self._login()
        history_page = next_orders_page.load_history_page()
        self.assertEqual(history_page.title, "Order history")

        # orders must be sorted by reverse delivery.date
        self.assertEqual(history_page.get_order_amount(0), closed_order1.amount)
        self.assertEqual(history_page.get_order_amount(1), closed_order2.amount)

        for order_index, order in enumerate([closed_order1, closed_order2]):
            history_page.open_order(order_index)
            self.assertIn(
                history_page.get_delivery_date(order_index),
                history_page.get_order_view_title(),
            )
            self.assertEqual(
                history_page.get_order_amount(order_index),
                history_page.get_order_view_amount(),
            )
            self.assertEqual(history_page.get_items_count(), order.items.count())
            for index, item in enumerate(order.items.all()):
                self.assertEqual(
                    history_page.get_item_unit_price(index), item.product_unit_price
                )
                self.assertEqual(history_page.get_item_name(index), item.product_name)
                self.assertEqual(history_page.get_item_quantity(index), item.quantity)
                self.assertEqual(history_page.get_item_amount(index), item.amount)
