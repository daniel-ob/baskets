from datetime import date, timedelta
from decimal import Decimal

from django.db.models import ProtectedError
from django.test import TestCase

from baskets.models import (
    Delivery,
    InactiveProductException,
    Order,
    OrderItem,
    Producer,
    Product,
)
from baskets.tests.common import (
    create_closed_delivery,
    create_opened_delivery,
    create_order_item,
    create_producer,
    create_product,
    create_user,
)


class ProducerTest(TestCase):
    def test_deactivate_deactivates_related_products(self):
        producer = create_producer()
        assert producer.is_active
        products = [create_product(producer) for _ in range(3)]

        producer.is_active = False
        producer.save()

        for product in products:
            product.refresh_from_db()
            self.assertFalse(product.is_active)

    def test_delete_deletes_releated_products(self):
        producer = create_producer()
        products = [create_product(producer) for _ in range(3)]

        producer.delete()

        self.assertNotIn(producer, Producer.objects.all())
        for product in products:
            self.assertNotIn(product, Product.objects.all())


class ProductTest(TestCase):
    def test_producer_products_count(self):
        producer1 = create_producer()
        producer2 = create_producer()
        [create_product(producer=producer1) for _ in range(2)]
        [create_product(producer=producer2) for _ in range(3)]

        self.assertEqual(producer1.products.count(), 2)
        self.assertEqual(producer2.products.count(), 3)

    def test_deactivate_removes_from_opened_deliveries_and_orders(self):
        product = create_product()
        opened_delivery = create_opened_delivery([product])
        closed_delivery = create_closed_delivery([product])
        opened_order_item = create_order_item(delivery=opened_delivery, product=product)
        closed_order_item = create_order_item(delivery=closed_delivery, product=product)

        product.is_active = False
        product.save()

        self.assertNotIn(opened_order_item, OrderItem.objects.all())
        self.assertNotIn(product, opened_delivery.products.all())
        # closed deliveries and order must not be affected
        self.assertIn(closed_order_item, OrderItem.objects.all())
        self.assertIn(product, closed_delivery.products.all())

    def test_delete_protect_if_order_items(self):
        product1 = create_product()
        product2 = create_product()
        opened_order_item = create_order_item(
            create_opened_delivery([product2]), product2
        )

        product1.delete()
        self.assertNotIn(product1, Product.objects.all())

        with self.assertRaises(ProtectedError):
            product2.delete()
        self.assertIn(opened_order_item, OrderItem.objects.all())

    def test_update_returns_list_of_user_ids_with_related_opened_items(self):
        product = create_product()
        opened_order_items = [
            create_order_item(
                delivery=create_opened_delivery([product]),
                product=product,
            )
            for _ in range(3)
        ]
        # same user has 2 items
        user = opened_order_items[0].order.user
        opened_order_items.append(
            create_order_item(
                delivery=create_opened_delivery([product]),
                product=product,
                user=user,
            )
        )
        # closed order items
        for _ in range(3):
            create_order_item(
                delivery=create_closed_delivery([product]),
                product=product,
            )

        user_id_list = product.save()

        expected_user_id_list = {
            oi.order.user.id for oi in opened_order_items
        }  # user must not be duplicated on list
        self.assertCountEqual(
            expected_user_id_list, user_id_list
        )  # both have the same elements

    def test_unit_price_update_updates_opened_order_amount(self):
        product = create_product()
        # order with just one item
        opened_order_item = create_order_item(
            delivery=create_opened_delivery(products=[product]), product=product
        )

        product.unit_price += 1
        product.save()

        opened_order_item.refresh_from_db()
        new_amount = opened_order_item.quantity * product.unit_price
        self.assertEqual(opened_order_item.amount, new_amount)
        self.assertEqual(opened_order_item.order.amount, new_amount)

    def test_update_doesnt_update_closed_orders(self):
        product = Product.objects.create(
            producer=create_producer(), name="product1", unit_price=Decimal("0.50")
        )
        # order with just one item
        closed_order_item = create_order_item(
            delivery=create_closed_delivery(products=[product]), product=product
        )
        initial_amount = closed_order_item.amount

        product.name = "product1 updated"
        product.unit_price += 1
        product.save()

        closed_order_item.refresh_from_db()
        self.assertEqual(closed_order_item.amount, initial_amount)
        self.assertEqual(closed_order_item.product_name, "product1")
        self.assertEqual(closed_order_item.product_unit_price, Decimal("0.50"))
        self.assertEqual(closed_order_item.order.amount, initial_amount)


class DeliveryTest(TestCase):
    def test_product_deliveries_count(self):
        product1 = create_product()
        product2 = create_product()
        create_closed_delivery(products=[product1, product2])
        create_opened_delivery(products=[product1])

        self.assertEqual(product1.deliveries.count(), 2)
        self.assertEqual(product2.deliveries.count(), 1)

    def test_deadline_auto(self):
        """Check that delivery.order_deadline is set to ORDER_DEADLINE_DAYS_BEFORE days before delivery.date
        when it's not specified at delivery creation"""

        d_date = date.today() + timedelta(days=7)
        d = Delivery.objects.create(date=d_date)
        self.assertEqual(
            d.order_deadline,
            d.date - timedelta(days=Delivery.ORDER_DEADLINE_DAYS_BEFORE),
        )

    def test_deadline_custom(self):
        d_date = date.today() + timedelta(days=15)
        d_deadline = d_date - timedelta(days=2)
        d = Delivery.objects.create(date=d_date, order_deadline=d_deadline)
        self.assertEqual(d.order_deadline, d_deadline)

    def test_product_remove_deletes_opened_order_items(self):
        product = create_product()
        opened_delivery = create_opened_delivery(products=[product])
        closed_delivery = create_closed_delivery(products=[product])
        opened_order_item = create_order_item(delivery=opened_delivery, product=product)
        closed_order_item = create_order_item(delivery=closed_delivery, product=product)

        opened_delivery.products.remove(product)
        closed_delivery.products.remove(product)

        self.assertNotIn(opened_order_item, OrderItem.objects.all())
        # closed_order_items must not be deleted
        self.assertIn(closed_order_item, OrderItem.objects.all())

    def test_cant_add_inactive_product_to_delivery(self):
        product = create_product()
        product.is_active = False
        product.save()
        delivery = create_opened_delivery()

        with self.assertRaises(InactiveProductException):
            delivery.products.add(product)


class OrderTest(TestCase):
    def setUp(self):
        self.user = create_user()
        self.delivery1 = create_opened_delivery()
        # self.user orders
        create_order_item(delivery=self.delivery1, user=self.user)
        create_order_item(delivery=create_closed_delivery(), user=self.user)
        # order from another user
        create_order_item(delivery=self.delivery1)

    def test_user_orders_count(self):
        self.assertEqual(self.user.orders.count(), 2)

    def test_delivery_orders_count(self):
        self.assertEqual(self.delivery1.orders.count(), 2)

    def test_amount(self):
        product1 = create_product()
        product2 = create_product()
        delivery = create_opened_delivery(products=[product1, product2])
        order = Order.objects.create(delivery=delivery, user=self.user)
        order.items.create(product=product1, quantity=2)
        order.items.create(product=product2, quantity=3)

        self.assertEqual(
            order.amount,
            sum(item.quantity * item.product.unit_price for item in order.items.all()),
        )


class OrderItemTest(TestCase):
    def test_order_items_count(self):
        delivery = create_opened_delivery(products=[create_product() for _ in range(3)])
        order = Order.objects.create(delivery=delivery, user=create_user())
        for product in delivery.products.all():
            order.items.create(product=product, quantity=2)

        self.assertEqual(order.items.count(), 3)

    def test_amount_opened_item(self):
        product = create_product()
        opened_order_item = create_order_item(
            delivery=create_opened_delivery(products=[product]),
            product=product,
        )
        self.assertEqual(
            opened_order_item.amount, opened_order_item.quantity * product.unit_price
        )
        opened_order_item.quantity += 1
        opened_order_item.save()
        product.unit_price += 1
        product.save()
        opened_order_item.refresh_from_db()
        self.assertEqual(
            opened_order_item.amount, opened_order_item.quantity * product.unit_price
        )

    def test_amount_closed_item(self):
        """At creation, amount is calculated using product.unit_price, afterward using saved product_unit_price"""

        product = create_product()
        closed_order_item = create_order_item(
            delivery=create_closed_delivery(products=[product]),
            product=product,
        )
        self.assertEqual(
            closed_order_item.amount, closed_order_item.quantity * product.unit_price
        )

        closed_order_item.quantity += 1
        closed_order_item.product_unit_price += 1
        closed_order_item.save()
        # product.unit_price update doesn't affect amount (see ProductTest.test_update_doesnt_update_closed_orders)
        self.assertEqual(
            closed_order_item.amount,
            closed_order_item.quantity * closed_order_item.product_unit_price,
        )

    def test_quantity_update_updates_order_amount(self):
        opened_order_item = create_order_item(delivery=create_opened_delivery())
        opened_order_item_initial_amount = opened_order_item.amount
        opened_order = opened_order_item.order
        closed_order_item = create_order_item(delivery=create_closed_delivery())
        closed_order_item_initial_amount = closed_order_item.amount
        closed_order = closed_order_item.order

        opened_order_item.quantity += 1
        opened_order_item.save()
        assert opened_order_item.amount != opened_order_item_initial_amount
        closed_order_item.quantity += 1
        closed_order_item.save()
        assert closed_order_item.amount != closed_order_item_initial_amount

        self.assertEqual(opened_order.amount, opened_order_item.amount)
        self.assertEqual(closed_order.amount, closed_order_item.amount)

    def test_delete_updates_order(self):
        user = create_user()
        product1 = create_product()
        product2 = create_product()
        opened_order1 = Order.objects.create(
            delivery=create_opened_delivery(products=[product1, product2]), user=user
        )
        opened_order1.items.create(product=product1, quantity=1)
        opened_order1.items.create(product=product2, quantity=2)
        closed_order1 = Order.objects.create(
            delivery=create_closed_delivery(products=[product1, product2]), user=user
        )
        closed_order1.items.create(product=product1, quantity=2)
        closed_order1.items.create(product=product2, quantity=3)
        # orders with only one item
        opened_order2 = create_order_item(delivery=create_opened_delivery()).order
        closed_order2 = create_order_item(delivery=create_closed_delivery()).order

        opened_order1.items.first().delete()
        closed_order1.items.first().delete()
        opened_order1.refresh_from_db()
        closed_order1.refresh_from_db()
        self.assertEqual(opened_order1.amount, opened_order1.items.last().amount)
        self.assertEqual(opened_order2.amount, opened_order2.items.last().amount)

        # orders with only one item should be also deleted
        opened_order2.items.first().delete()
        closed_order2.items.first().delete()
        self.assertNotIn(opened_order2, Order.objects.all())
        self.assertNotIn(closed_order2, Order.objects.all())
