from datetime import date, timedelta

from baskets.models import Delivery, Order, OrderItem, User, Product
from baskets.tests.setup import BasketsTestCase


class ModelsTestCase(BasketsTestCase):
    def test_producer_products_count(self):
        self.assertEqual(self.producer1.products.count(), 2)
        self.assertEqual(self.producer2.products.count(), 1)

    def test_product_deliveries_count(self):
        self.assertEqual(self.product1.deliveries.count(), 3)

    def test_product_soft_delete(self):
        """Test that by default, a product is not deleted but just deactivated"""
        product = self.create_product()
        opened_delivery = self.create_opened_delivery([product])
        opened_order_item = self.create_order_item(
            delivery=opened_delivery,
            product=product
        )
        closed_order_item = self.create_order_item(
            delivery=self.create_closed_delivery([product]),
            product=product
        )

        product.delete()

        self.assertIn(product, Product.objects.all())
        self.assertFalse(product.is_active)

    def test_product_hard_delete(self):
        product = self.create_product()
        opened_delivery = self.create_opened_delivery([product])
        closed_order_item = self.create_order_item(
            delivery=self.create_closed_delivery([product]),
            product=product
        )

        product.delete(soft_delete=False)

        self.assertNotIn(product, Product.objects.all())

    def test_product_delete_returns_users_list(self):
        """Check that product.delete() returns list of user ids with related opened orders"""

        product = self.create_product()
        opened_delivery = self.create_opened_delivery([product])
        closed_delivery = self.create_closed_delivery([product])
        opened_order_items = [self.create_order_item(opened_delivery, product) for _ in range(3)]
        closed_order_items = [self.create_order_item(closed_delivery, product) for _ in range(3)]

        user_id_list = product.delete()

        expected_user_id_list = [oi.order.user.id for oi in opened_order_items]
        self.assertCountEqual(expected_user_id_list, user_id_list)  # have same elements

    def test_update_opened_delivery_products_on_product_delete(self):
        product = self.create_product()
        opened_delivery = self.create_opened_delivery([product])
        closed_delivery = self.create_closed_delivery([product])

        product.delete()

        self.assertNotIn(product, opened_delivery.products.all())
        # closed delivery products must not be updated
        self.assertIn(product, closed_delivery.products.all())

    def test_user_orders_count(self):
        self.assertEqual(self.u1.orders.count(), 2)

    def test_delivery_orders_count(self):
        self.assertEqual(self.d1.orders.count(), 1)

    def test_delivery_deadline_auto(self):
        """Check that delivery.order_deadline is set to ORDER_DEADLINE_DAYS_BEFORE days before delivery.date
        when it's not specified at delivery creation"""

        yesterday = date.today() - timedelta(days=1)
        d = Delivery.objects.create(date=yesterday)
        self.assertEqual(d.order_deadline, d.date - timedelta(days=self.d1.ORDER_DEADLINE_DAYS_BEFORE))

    def test_delivery_deadline_custom(self):
        self.assertEqual(self.d2.order_deadline, date.today())

    def test_order_items_count(self):
        self.assertEqual(self.o1.items.count(), 2)

    def test_items_amount(self):
        self.assertEqual(self.o1i1.amount, 2)
        self.assertEqual(self.o1i2.amount, 1)

    def test_order_amount(self):
        self.assertEqual(self.o1.amount, 3)

    def test_order_amount_update_on_item_quantity_update(self):
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

    def test_order_amount_update_on_item_delete(self):
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

    def test_opened_order_amount_update_on_product_price_update(self):
        """Test that opened order updates its amounts (total and items) when related product unit price is updated"""

        self.assertTrue(self.o2.is_open)

        self.product1.unit_price += 0.25
        self.product1.save()

        [elem.refresh_from_db() for elem in [self.o2, self.o2i1]]
        self.assertEqual(float(self.o2i1.amount), 0.75)
        self.assertEqual(float(self.o2.amount), 4.20)

    def test_opened_order_update_on_product_delete(self):
        """Check that order item is deleted when related product is deleted.
        Then, if order has no more items remaining, it's also deleted"""

        # order with two items
        self.assertTrue(self.o2.is_open)
        self.assertEqual(self.o2.items.count(), 2)

        # order with one item (this order must be deleted)
        self.assertTrue(self.o3.is_open)
        self.assertEqual(self.o3.items.count(), 1)

        self.product1.delete()

        self.o2.refresh_from_db()
        self.assertEqual(self.o2.items.count(), 1)
        self.assertEqual(float(self.o2.amount), 3.45)

        with self.assertRaises(OrderItem.DoesNotExist):
            OrderItem.objects.get(id=self.o3i1.id)
        with self.assertRaises(Order.DoesNotExist):
            Order.objects.get(id=self.o3.id)

    def test_closed_order_persistence_on_product_update_or_delete(self):
        """Test that closed order keeps amounts (total and items) and saved product info unchanged when related products
        are updated or deleted"""

        self.assertFalse(self.o1.is_open)
        self.assertEqual(self.o1.items.count(), 2)

        initial_item1_amount = self.o1i1.amount
        initial_item2_amount = self.o1i2.amount
        initial_order_amount = self.o1.amount

        self.product1.name = "product1 updated"
        self.product1.unit_price += 1.00
        self.product1.save()
        self.product2.delete()

        [elem.refresh_from_db() for elem in [self.o1, self.o1i1, self.o1i2]]
        self.assertEqual(self.o1.items.count(), 2)
        self.assertEqual(self.o1i1.saved_p_name, "product1")
        self.assertEqual(self.o1i1.saved_p_unit_price, 0.50)
        self.assertEqual(self.o1i1.amount, initial_item1_amount)
        self.assertEqual(self.o1i2.amount, initial_item2_amount)
        self.assertEqual(self.o1.amount, initial_order_amount)

    def test_closed_order_amount_update_on_saved_product_price_update(self):
        """Check that closed order updates its amounts (total and item) when saved product unit price is updated"""

        self.assertFalse(self.o1.is_open)

        self.o1i1.saved_p_unit_price += 0.25
        self.o1i1.save()

        self.assertEqual(self.o1i1.amount, 3.00)
        self.assertEqual(self.o1.amount, 4.00)

    def test_valid_order_item(self):
        """Check that order item is valid if product is available in delivery and quantity is greater than 0"""

        self.assertEqual(self.o1i1.is_valid(), True)
        self.assertEqual(self.o1i2.is_valid(), True)

    def test_order_item_remove_on_opened_delivery_product_remove(self):
        """Check that when a product is removed from an opened delivery, related order_items are deleted"""

        product = self.create_product()
        opened_delivery = self.create_opened_delivery([product])
        closed_delivery = self.create_closed_delivery([product])
        opened_order_item = self.create_order_item(opened_delivery, product)
        closed_order_item = self.create_order_item(closed_delivery, product)

        opened_delivery.products.remove(product)
        closed_delivery.products.remove(product)

        self.assertNotIn(opened_order_item, OrderItem.objects.all())
        # order_items related to closed delivery must not be removed
        self.assertIn(closed_order_item, OrderItem.objects.all())

    def test_invalid_order_item_product(self):
        """Check that order item is invalid if product is not available in delivery"""

        order_item = OrderItem.objects.create(order=self.o3, product=self.product2, quantity=1)
        self.assertFalse(order_item.is_valid())

    def test_invalid_order_item_quantity(self):
        """Check that order item is invalid if quantity is not greater than 0"""

        order_item = OrderItem.objects.create(order=self.o3, product=self.product1, quantity=0)
        self.assertFalse(order_item.is_valid())
