from datetime import date, timedelta

from django.db.models import ProtectedError

from baskets.models import (
    Delivery,
    InactiveProductException,
    OrderItem,
    Product,
    Producer,
)
from baskets.tests.common import (
    BasketsTestCase,
    create_producer,
    create_product,
    create_opened_delivery,
    create_closed_delivery,
    create_order_item,
)


class ProducerTest(BasketsTestCase):
    def test_deactivate(self):
        """When a producer is deactivated, related products must be also deactivated"""

        producer = create_producer()
        assert producer.is_active
        products = [create_product(producer) for _ in range(3)]

        producer.is_active = False
        producer.save()

        for product in products:
            product.refresh_from_db()
            self.assertFalse(product.is_active)

    def test_delete(self):
        """When a producer is deleted, related products must be also deleted"""

        producer = create_producer()
        products = [create_product(producer) for _ in range(3)]

        producer.delete()

        self.assertNotIn(producer, Producer.objects.all())
        for product in products:
            self.assertNotIn(product, Product.objects.all())


class ProductTest(BasketsTestCase):
    def test_producer_products_count(self):
        self.assertEqual(self.producer1.products.count(), 2)
        self.assertEqual(self.producer2.products.count(), 1)

    def test_deactivate(self):
        """When a product is deactivated it should be removed from opened deliveries and opened orders.
        It should be kept in closed deliveries and orders"""

        product = create_product()
        opened_delivery = create_opened_delivery([product])
        closed_delivery = create_closed_delivery([product])
        opened_order_item = create_order_item(delivery=opened_delivery, product=product)
        closed_order_item = create_order_item(delivery=closed_delivery, product=product)

        product.is_active = False
        product.save()

        self.assertIn(closed_order_item, OrderItem.objects.all())
        self.assertNotIn(opened_order_item, OrderItem.objects.all())
        self.assertIn(product, closed_delivery.products.all())
        self.assertNotIn(product, opened_delivery.products.all())

    def test_delete_protect(self):
        """Check that a product can't be deleted if it has any related order_items."""

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

    def test_update_returns_users_list(self):
        """Check that when a product is updated, product.save() returns list of user ids with related opened orders"""

        product = create_product()
        opened_delivery = create_opened_delivery([product])
        closed_delivery = create_closed_delivery([product])
        opened_order_items = [
            create_order_item(opened_delivery, product) for _ in range(3)
        ]
        # closed order items
        [create_order_item(closed_delivery, product) for _ in range(3)]

        user_id_list = product.save()

        expected_user_id_list = [oi.order.user.id for oi in opened_order_items]
        self.assertCountEqual(expected_user_id_list, user_id_list)  # have same elements

    def test_unit_price_update_updates_opened_order_amount(self):
        self.assertTrue(self.o2.is_open)

        self.product1.unit_price += 0.25
        self.product1.save()

        self.o2i1.refresh_from_db()
        self.assertEqual(float(self.o2i1.amount), 0.75)
        self.o2.refresh_from_db()
        self.assertEqual(float(self.o2.amount), 4.20)

    def test_update_doesnt_update_closed_orders(self):
        self.assertFalse(self.o1.is_open)
        self.assertEqual(self.o1.items.count(), 2)

        initial_item1_amount = self.o1i1.amount
        initial_order_amount = self.o1.amount

        self.product1.name = "product1 updated"
        self.product1.unit_price += 1.00
        self.product1.save()

        self.o1.refresh_from_db()
        self.assertEqual(self.o1.amount, initial_order_amount)
        self.o1i1.refresh_from_db()
        self.assertEqual(self.o1i1.product_name, "product1")
        self.assertEqual(self.o1i1.product_unit_price, 0.50)
        self.assertEqual(self.o1i1.amount, initial_item1_amount)


class DeliveryTest(BasketsTestCase):
    def test_product_deliveries_count(self):
        self.assertEqual(self.product1.deliveries.count(), 3)

    def test_deadline_auto(self):
        """Check that delivery.order_deadline is set to ORDER_DEADLINE_DAYS_BEFORE days before delivery.date
        when it's not specified at delivery creation"""

        yesterday = date.today() - timedelta(days=1)
        d = Delivery.objects.create(date=yesterday)
        self.assertEqual(
            d.order_deadline,
            d.date - timedelta(days=self.d1.ORDER_DEADLINE_DAYS_BEFORE),
        )

    def test_deadline_custom(self):
        self.assertEqual(self.d2.order_deadline, date.today())

    def test_product_remove_removes_opened_order_item(self):
        """Check that when a product is removed from an opened delivery, related order_items are deleted"""

        product = create_product()
        opened_delivery = create_opened_delivery([product])
        closed_delivery = create_closed_delivery([product])
        opened_order_item = create_order_item(opened_delivery, product)
        closed_order_item = create_order_item(closed_delivery, product)

        opened_delivery.products.remove(product)
        closed_delivery.products.remove(product)

        self.assertNotIn(opened_order_item, OrderItem.objects.all())
        # order_items related to closed delivery must not be removed
        self.assertIn(closed_order_item, OrderItem.objects.all())

    def test_cant_add_inactive_product_to_delivery(self):
        product = create_product()
        product.is_active = False
        product.save()
        delivery = create_opened_delivery()

        with self.assertRaises(InactiveProductException):
            delivery.products.add(product)


class OrderTest(BasketsTestCase):
    def test_user_orders_count(self):
        self.assertEqual(self.u1.orders.count(), 2)

    def test_delivery_orders_count(self):
        self.assertEqual(self.d1.orders.count(), 1)

    def test_amount(self):
        self.assertEqual(self.o1.amount, 3)


class OrderItemTest(BasketsTestCase):
    def test_order_items_count(self):
        self.assertEqual(self.o1.items.count(), 2)

    def test_amount(self):
        self.assertEqual(self.o1i1.amount, 2)
        self.assertEqual(self.o1i2.amount, 1)

    def test_quantity_update_updates_order_amount(self):
        """Check that order updates its amounts (item and total) when item quantity is updated"""

        # closed order
        self.assertFalse(self.o1.is_open)
        self.o1i1.quantity += 1
        self.o1i1.save()

        # opened order
        self.assertTrue(self.o2.is_open)
        self.o2i1.quantity += 1
        self.o2i1.save()

        self.assertEqual(self.o1i1.amount, 2.50)
        self.assertEqual(float(self.o1.amount), 3.50)

        self.assertEqual(self.o2i1.amount, 1.00)
        self.assertEqual(float(self.o2.amount), 4.45)

    def test_saved_product_price_update_updates_closed_order_amount(self):
        """Check that closed order updates its amounts (total and item) when saved product unit price is updated"""

        self.assertFalse(self.o1.is_open)

        self.o1i1.product_unit_price += 0.25
        self.o1i1.save()

        self.o1i1.refresh_from_db()
        self.assertEqual(self.o1i1.amount, 3.00)
        self.assertEqual(self.o1.amount, 4.00)

    def test_delete_updates_order_amount(self):
        """Check that order amount is updated when one of its items is deleted"""

        # closed order
        self.assertEqual(self.o1.items.count(), 2)
        self.o1i1.delete()

        # opened order
        self.assertEqual(self.o2.items.count(), 2)
        self.o2i1.delete()

        self.assertEqual(self.o1.items.count(), 1)
        self.assertEqual(float(self.o1.amount), 1.00)

        self.assertEqual(self.o2.items.count(), 1)
        self.assertEqual(float(self.o2.amount), 3.45)
