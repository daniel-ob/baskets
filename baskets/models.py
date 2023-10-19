from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum, UniqueConstraint
from django.db.models.signals import m2m_changed
from django.utils.translation import gettext_lazy as _

from config.settings import FR_PHONE_REGEX


class Producer(models.Model):
    name = models.CharField(_("name"), blank=False, max_length=64)
    phone = models.CharField(
        _("phone"), blank=True, validators=[FR_PHONE_REGEX], max_length=18
    )
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("producer")
        ordering = ["-is_active", "name"]

    def __str__(self):
        return f"{self.name}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.is_active:
            for product in self.products.all():
                product.is_active = False
                product.save()


class Product(models.Model):
    producer = models.ForeignKey(
        Producer,
        on_delete=models.CASCADE,
        related_name="products",
    )
    name = models.CharField(_("name"), blank=False, max_length=64)
    unit_price = models.DecimalField(
        _("unit price"), blank=False, max_digits=8, decimal_places=2
    )
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("product")
        ordering = ["producer", "name"]  # for "Next Orders" and "DeliveryAdmin" pages

    def __str__(self):
        return f"{self.name}" if self.is_active else f"({self.name})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_active and not self.producer.is_active:
            self.producer.is_active = True
            self.producer.save()
        opened_order_items_list, user_id_list = self._get_opened_order_items_and_users()
        for oi in opened_order_items_list:
            oi.save()
        if not self.is_active:
            self._delete_from_opened_deliveries()
        return user_id_list

    def _get_opened_order_items_and_users(self):
        opened_order_items_list = [
            oi for oi in self.order_items.all() if oi.order.is_open
        ]
        user_id_list = list(
            get_user_model()
            .objects.filter(orders__items__in=opened_order_items_list)
            .distinct()
            .values_list("id", flat=True)
        )  # use list(id) because User QuerySet would be empty when order_items are deleted
        return opened_order_items_list, user_id_list

    def _delete_from_opened_deliveries(self):
        for d in Delivery.objects.filter(
            products__in=[self], order_deadline__gte=date.today()
        ):
            d.products.remove(self)


class InactiveProductException(Exception):
    pass


class Delivery(models.Model):
    ORDER_DEADLINE_DAYS_BEFORE = 4
    ORDER_DEADLINE_HELP_TEXT = _(
        "Last day to order. If left blank, it will be automatically set to {} days before Delivery date"
    ).format(ORDER_DEADLINE_DAYS_BEFORE)

    date = models.DateField(blank=False, unique=True)
    order_deadline = models.DateField(
        _("last day to order"),
        blank=True,
        help_text=ORDER_DEADLINE_HELP_TEXT,  # for admin interface
    )
    products = models.ManyToManyField(
        Product,
        verbose_name=_("products"),
        related_name="deliveries",
        help_text="All products on the left. "
        "On the right, products available for this delivery.<br>",  # for /admin
    )
    message = models.CharField(blank=True, max_length=128)

    class Meta:
        verbose_name = _("delivery")
        verbose_name_plural = _("deliveries")
        ordering = ["date"]

    def save(self, *args, **kwargs):
        if not self.order_deadline:
            self.order_deadline = self.date - timedelta(
                days=self.ORDER_DEADLINE_DAYS_BEFORE
            )
        super().save(*args, **kwargs)

    @property
    def is_open(self):
        return date.today() <= self.order_deadline

    def __str__(self):
        return f"{self.date}"


def delivery_product_removed(action, instance, pk_set, **kwargs):
    if action == "post_remove" and instance.is_open:
        OrderItem.objects.filter(
            product__id__in=pk_set, order__delivery=instance
        ).delete()


def delivery_product_add(action, instance, pk_set, **kwargs):
    if (
        action == "pre_add"
        and instance.is_open
        and Product.objects.filter(pk__in=pk_set, is_active=False)
    ):
        raise InactiveProductException("Can't add inactive product to delivery")


m2m_changed.connect(delivery_product_removed, sender=Delivery.products.through)
m2m_changed.connect(delivery_product_add, sender=Delivery.products.through)


class Order(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("user"),
        on_delete=models.PROTECT,
        related_name="orders",
    )
    delivery = models.ForeignKey(
        Delivery,
        verbose_name=_("delivery"),
        on_delete=models.PROTECT,
        related_name="orders",
    )
    creation_date = models.DateTimeField(_("creation date"), auto_now_add=True)
    last_updated_date = models.DateTimeField(_("last update date"), auto_now=True)
    amount = models.DecimalField(
        _("amount"), default=0.00, max_digits=8, decimal_places=2, editable=False
    )
    message = models.CharField(
        blank=True,
        max_length=128,
        help_text=_("Internal message only visible by stuff members"),
    )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["delivery", "user"],
                name="user can only place one order per delivery",
            )
        ]
        verbose_name = _("order")

    def save(self, *args, **kwargs):
        order_items = self.items.all()
        self.amount = (
            order_items.aggregate(Sum("amount"))["amount__sum"] if order_items else 0.00
        )
        super().save(*args, **kwargs)

    @property
    def is_open(self):
        return self.delivery.is_open

    def __str__(self):
        return _("From {user} for {delivery}").format(
            user=self.user, delivery=self.delivery.date
        )


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, verbose_name=_("order"), on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(
        to=Product,
        null=True,  # possible when order is closed
        blank=True,  # possible when order is closed
        verbose_name=_("product"),
        on_delete=models.PROTECT,
        related_name="order_items",
    )
    quantity = models.PositiveIntegerField(
        _("quantity"), null=False, default=1, validators=[MinValueValidator(1)]
    )
    amount = models.DecimalField(
        _("amount"), default=0.00, max_digits=8, decimal_places=2, editable=False
    )

    # saved product data to prevent inconsistencies due to product update
    product_name = models.CharField(
        _("product name (saved)"), null=True, blank=True, max_length=64
    )
    product_unit_price = models.DecimalField(
        _("product unit price (saved)"),
        null=True,
        blank=True,
        max_digits=8,
        decimal_places=2,
    )

    class Meta:
        verbose_name = _("order item")
        verbose_name_plural = _("order items")

    def save(self, *args, **kwargs):
        self._update_saved_product_data()
        self._update_amount()
        super().save(*args, **kwargs)
        # Recalculate order.amount with this item
        self.order.save()

    def _update_saved_product_data(self):
        """Saved product data is updated for opened orders and initialized when creating closed ones (tests or admin)"""

        if self.order.is_open or not self.product_unit_price:
            self.product_name = self.product.name
            self.product_unit_price = self.product.unit_price

    def _update_amount(self):
        unit_price = (
            self.product.unit_price if self.order.is_open else self.product_unit_price
        )
        self.amount = self.quantity * unit_price

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        # Recalculate related order.amount
        self.order.save()
        if not self.order.items.count():
            self.order.delete()

    def clean(self):
        if (
            hasattr(
                self.order, "delivery"
            )  # prevent error on saving OrderItemInline if no delivery is set
            and self.product not in self.order.delivery.products.all()
        ):
            raise ValidationError(
                _("product '{}' not available on this delivery").format(self.product)
            )

    def __str__(self):
        return f"{self.order}: {self.quantity} x {self.product_name}"
