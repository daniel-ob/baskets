from datetime import date, timedelta

from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator, MinValueValidator
from django.db import models
from django.db.models import Sum, UniqueConstraint
from django.db.models.signals import m2m_changed
from django.utils.translation import gettext_lazy as _

# FR phone numbers regex
PHONE_REGEX = RegexValidator(regex=r"^"
                                   r"(?:(?:\+|00)33|0)"     # Dialing code
                                   r"\s*[1-9]"              # First number (from 1 to 9)
                                   r"(?:[\s.-]*\d{2}){4}"   # End of the phone number
                                   r"$")


class User(AbstractUser):
    # make last_name and email mandatory
    last_name = models.CharField(_('last name'), max_length=150, blank=False)
    email = models.EmailField(_('email address'), blank=False)

    # add new fields
    phone = models.CharField("téléphone", blank=True, validators=[PHONE_REGEX], max_length=18)
    address = models.CharField("adresse", blank=True, max_length=128)

    class Meta:
        verbose_name = "utilisateur"
        ordering = ["username"]

    def __str__(self):
        return f"{self.username}"


class Producer(models.Model):
    name = models.CharField("nom", blank=False, max_length=64)
    phone = models.CharField("téléphone", blank=True, validators=[PHONE_REGEX], max_length=18)
    email = models.EmailField(blank=True)

    class Meta:
        verbose_name = "producteur"
        ordering = ["name"]

    def serialize(self, delivery_id_to_filter_products=None):
        if delivery_id_to_filter_products is not None:
            products_to_show = self.products.filter(deliveries__id=delivery_id_to_filter_products)
        else:
            products_to_show = self.products.all()
        products_to_show = products_to_show.filter(is_active=True)
        return {
            "id": self.id,
            "name": self.name,
            "products": [product.serialize() for product in products_to_show]
        }

    def __str__(self):
        return f"{self.name}"


class Product(models.Model):
    producer = models.ForeignKey(Producer, verbose_name="producteur", on_delete=models.CASCADE, related_name="products")
    name = models.CharField("nom", blank=False, max_length=64)
    unit_price = models.DecimalField("prix unitaire", blank=False, max_digits=8, decimal_places=2)
    is_active = models.BooleanField(default=True)  # for soft-delete

    class Meta:
        verbose_name = "produit"
        ordering = ["producer", "name"]  # for "Next Orders" and "DeliveryAdmin" pages

    def serialize(self):
        return {
            "id": self.id,
            "name": self.name,
            "unit_price": self.unit_price
        }

    def __str__(self):
        return f"{self.name}"

    def delete(self, soft_delete=True, *args, **kwargs):
        if soft_delete:
            self.is_active = False
            self.save()
        else:
            super().delete(*args, **kwargs)
        # Delete related opened order items (and order if empty)
        opened_order_items, user_id_list = self.get_opened_order_items_and_users()
        [oi.delete() for oi in opened_order_items]
        # Delete product from opened deliveries
        for d in Delivery.objects.filter(products__in=[self], order_deadline__gte=date.today()):
            d.products.remove(self)
        return user_id_list

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # update related opened order items
        opened_order_items, user_id_list = self.get_opened_order_items_and_users()
        for oi in opened_order_items:
            oi.save()
        return user_id_list

    def get_opened_order_items_and_users(self):
        opened_order_items = [oi for oi in OrderItem.objects.filter(product=self) if oi.order.is_open]
        # can't use user QuerySet based on order_items because they will be deleted, so query will be empty later
        user_id_list = [u.id for u in User.objects.filter(orders__items__in=opened_order_items).distinct()]
        return opened_order_items, user_id_list


class Delivery(models.Model):
    ORDER_DEADLINE_DAYS_BEFORE = 4
    ORDER_DEADLINE_HELP_TEXT = f"Date limite de commande.<br> Si pas définie, elle sera automatiquement fixée à " \
                               f"{ORDER_DEADLINE_DAYS_BEFORE} jours avant la Date de Livraison"

    date = models.DateField(blank=False)
    order_deadline = models.DateField(
        "date limite de commande",
        blank=True,
        unique=True,
        help_text=ORDER_DEADLINE_HELP_TEXT  # for /admin
    )
    products = models.ManyToManyField(
        Product,
        verbose_name="produits",
        related_name="deliveries",
        help_text="A gauche tous les produits. "
                  "A droite les produits disponibles à la commande pour cette livraison<br>"  # for /admin
    )
    message = models.CharField(blank=True, max_length=128)

    class Meta:
        verbose_name = "livraison"
        ordering = ["date"]

    def serialize(self):
        delivery_producers = Producer.objects.filter(products__in=self.products.all()).distinct()
        return {
            "date": self.date,
            "order_deadline": self.order_deadline,
            "products_by_producer": [
                producer.serialize(delivery_id_to_filter_products=self.id)
                for producer in delivery_producers.all()
            ],
            "message": self.message,
            "is_open": self.is_open
        }

    def save(self, *args, **kwargs):
        if not self.order_deadline:
            self.order_deadline = self.date - timedelta(days=self.ORDER_DEADLINE_DAYS_BEFORE)
        super().save(*args, **kwargs)

    @property
    def is_open(self):
        """Delivery is open (accepts orders) until its order_deadline"""
        return date.today() <= self.order_deadline

    def __str__(self):
        return f"{self.date}"


def delivery_product_removed(action, instance, pk_set, **kwargs):
    """When a product is removed from an opened delivery, remove related order_items"""
    if action == "post_remove" and instance.is_open:
        if order_items := OrderItem.objects.filter(product__id__in=pk_set, order__delivery=instance):
            [oi.delete() for oi in order_items]


m2m_changed.connect(delivery_product_removed, sender=Delivery.products.through)


class Order(models.Model):
    user = models.ForeignKey(User, verbose_name="utilisateur", on_delete=models.PROTECT, related_name="orders")
    delivery = models.ForeignKey(Delivery, verbose_name="livraison", on_delete=models.PROTECT, related_name="orders")
    creation_date = models.DateTimeField("date de création", auto_now_add=True)
    amount = models.DecimalField("montant", default=0.00, max_digits=8, decimal_places=2, editable=False)
    message = models.CharField(blank=True, max_length=128, help_text="Message interne seulement visible par l'équipe")

    class Meta:
        constraints = [
            UniqueConstraint(fields=["delivery", "user"], name="user can only place one order per delivery")
        ]
        verbose_name = "commande"

    def serialize(self):
        return {
            "delivery_id": self.delivery.id,
            "items": [item.serialize() for item in self.items.all()],
            "amount": self.amount,
            "message": self.message,
            "is_open": self.is_open,
        }

    def save(self, *args, **kwargs):
        # Order amount is the sum of its items amounts
        order_items = self.items.all()
        self.amount = order_items.aggregate(Sum("amount"))["amount__sum"] if order_items else 0.00
        # Save order
        super().save(*args, **kwargs)

    @property
    def is_open(self):
        return self.delivery.is_open

    def __str__(self):
        return f"De {self.user} pour {self.delivery.date}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, verbose_name="commande", on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        to=Product,
        null=True,  # possible when order is closed
        blank=True,  # possible when order is closed
        verbose_name="produit",
        on_delete=models.SET_NULL,
        related_name="order_items",
    )
    quantity = models.PositiveIntegerField("quantité", null=False, default=1, validators=[MinValueValidator(1)])
    amount = models.DecimalField("montant", default=0.00, max_digits=8, decimal_places=2, editable=False)

    # product data to be used for closed orders to prevent inconsistencies (due to product update or delete)
    saved_p_name = models.CharField("nom du produit (sauvegardé)", null=True, blank=True, max_length=64)
    saved_p_unit_price = models.DecimalField("prix unitaire (sauvegardé)", null=True, blank=True, max_digits=8,
                                             decimal_places=2)

    class Meta:
        verbose_name = "ligne de commande"
        verbose_name_plural = "lignes de commande"

    def serialize(self):
        return {
            "product": self.product.serialize() if self.order.is_open else {
                "name": self.saved_p_name,
                "unit_price": self.saved_p_unit_price,
            },
            "quantity": self.quantity,
            "amount": self.amount,
        }

    def save(self, *args, **kwargs):
        if self.order.is_open or (
            not self.saved_p_unit_price and self.product  # to create closed orders
        ):
            self.saved_p_name = self.product.name
            self.saved_p_unit_price = self.product.unit_price
            self.amount = self.quantity * self.product.unit_price
        else:
            self.amount = self.quantity * self.saved_p_unit_price
        # Save item
        super().save(*args, **kwargs)
        # Recalculate order.amount with this item
        self.order.save()

    def delete(self, *args, **kwargs):
        # Delete item
        super().delete(*args, **kwargs)
        # Recalculate related order.amount
        self.order.save()
        # Delete empty order
        if not self.order.items.count():
            self.order.delete()

    def is_valid(self):
        """Order item is valid if product is available in related delivery and quantity is greater than 0"""
        return self.product in self.order.delivery.products.all() and self.quantity > 0

    def __str__(self):
        product_name = self.product.name if self.product else self.saved_p_name
        return f"{self.order}: {self.quantity} x {product_name}"
