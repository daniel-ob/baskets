from datetime import date

from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.db.models import Case, Count, Sum, When
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from .models import Delivery, Order, OrderItem, Producer, Product

User = get_user_model()


def show_message_email_users(request, status_message, user_id_list):
    emails_str = ", ".join(
        User.objects.filter(id__in=user_id_list).values_list("email", flat=True)
    )
    link_text = _("Email affected users")
    messages.add_message(
        request,
        messages.SUCCESS,
        mark_safe(
            f"{status_message}<br>"
            f"<a href='mailto:?bcc={emails_str}'>{link_text}</a>"
        ),
    )


class ProductInline(admin.TabularInline):
    model = Product
    fields = ["name", "unit_price", "is_active"]
    ordering = ["-is_active", "name"]
    extra = 0


@admin.register(Producer)
class ProducerAdmin(admin.ModelAdmin):
    list_display = ["name_html"]
    inlines = [ProductInline]

    class Media:
        css = {"all": ("css/hide_admin_original.css",)}
        js = ("js/admin_add_help_text_to_productinline.js",)

    @admin.display(description="nom")
    def name_html(self, producer):
        if producer.is_active:
            return producer.name
        else:
            return format_html(f"<strike>{producer.name}</strike>")

    def save_formset(self, request, form, formset, change):
        """If a product is disabled or its unit_price changes, update related orders and show a message"""

        products_new_or_updated = formset.save(commit=False)  # don't save them yet
        for product in formset.deleted_objects:
            product.delete()
        for product in products_new_or_updated:
            try:
                product_from_db = Product.objects.get(pk=product.id)
                previous_price = product_from_db.unit_price
                previous_is_active = product_from_db.is_active
                user_id_list = (
                    product.save()
                )  # update product in DB and related opened order items
                if user_id_list:
                    if previous_is_active and not product.is_active:
                        show_message_email_users(
                            request,
                            _(
                                "Product '{}' has been removed from opened orders."
                            ).format(product),
                            user_id_list,
                        )
                    if product.unit_price != previous_price and user_id_list:
                        show_message_email_users(
                            request,
                            _("Product '{}' has been updated on opened orders.").format(
                                product
                            ),
                            user_id_list,
                        )
            except Product.DoesNotExist:  # new product
                product.save()
        formset.save_m2m()


class DeliveryProductInline(admin.TabularInline):
    model = Delivery.products.through
    verbose_name_plural = _("Total ordered quantities per product")
    readonly_fields = ["producer", "product", "total_ordered_quantity"]
    ordering = ["product__producer", "product__name"]
    extra = 0
    can_delete = False

    @admin.display(description=_("producer"))
    def producer(self, obj):
        return obj.product.producer

    @admin.display(description=_("total ordered quantity"))
    def total_ordered_quantity(self, obj):
        d = obj.delivery
        p = obj.product
        order_items = p.order_items.filter(order__delivery=d)
        total_quantity = order_items.aggregate(Sum("quantity"))["quantity__sum"]
        order_items_admin_url = (
            f"{reverse('admin:baskets_orderitem_changelist')}"
            f"?order__delivery__id__exact={d.id}&product__id__exact={p.id}"
        )

        return (
            format_html(f"<a href='{order_items_admin_url}'>{total_quantity}</a>")
            if total_quantity
            else 0
        )

    def has_add_permission(self, request, obj):
        """Hide 'add' line at the bottom of inline"""
        return False


@admin.action(description=_("Email users from selected deliveries"))
def mailto_users_from_deliveries(modeladmin, request, queryset):
    deliveries = queryset
    show_message_email_users(
        request,
        "",
        User.objects.filter(orders__delivery__in=deliveries).values("id"),
    )


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ("date", "orders_count", "export")
    ordering = ["-date"]
    filter_horizontal = ("products",)
    inlines = [DeliveryProductInline]
    actions = [mailto_users_from_deliveries]

    class Media:
        css = {"all": ("css/hide_admin_original.css",)}

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(Count("orders"))
        return qs

    @admin.display(description=_("number of orders"), ordering="orders__count")
    def orders_count(self, obj):
        delivery_orders_url = (
            reverse("admin:baskets_order_changelist") + f"?delivery__id__exact={obj.id}"
        )
        return format_html(f"<a href='{delivery_orders_url}'>{obj.orders__count}</a>")

    @admin.display(description=_("export"))
    def export(self, obj):
        d = obj
        delivery_export_url = reverse("delivery_export", args=[d.id])
        link_text = _("Export order forms")
        if d.orders.count() and not d.is_open:
            return format_html(f"<a href='{delivery_export_url}'>{link_text}</a>")
        else:
            return "-"

    def get_formsets_with_inlines(self, request, obj=None):
        """ "Override method to hide inline on add view"""
        for inline in self.get_inline_instances(request, obj):
            # show inline if obj exists
            if obj is not None:
                yield inline.get_formset(request, obj), inline

    def save_model(self, request, obj, form, change):
        """If a product is removed from an opened delivery, related opened order_items will be deleted by
        delivery_product_removed (triggered by m2m_changed signal).
        Here we show a message to notify concerned users
        """
        super().save_model(request, obj, form, change)

        d = obj
        if d.is_open and "products" in form.changed_data:
            previous_products = obj.products.all()
            new_products = form.cleaned_data["products"]
            if removed_products := previous_products.exclude(id__in=new_products):
                if related_order_items := OrderItem.objects.filter(
                    product__in=removed_products, order__delivery=d
                ):
                    products_html_list = "</li><li>".join(
                        removed_products.values_list("name", flat=True)
                    )
                    message_text = _(
                        "The following product(s) have been removed from opened orders:"
                    )
                    show_message_email_users(
                        request,
                        f"{message_text} <ul><li>{products_html_list}</li></ul>",
                        related_order_items.values("order__user__id"),
                    )

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Override method to show only active products"""
        if db_field.name == "products":
            kwargs["queryset"] = Product.objects.filter(is_active=True)
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class OrderIsOpenFilter(admin.SimpleListFilter):
    """Add filter by order.is_open property"""

    title = _("open")
    parameter_name = "open"

    def lookups(self, request, model_admin):
        return (
            ("yes", _("yes")),
            ("no", _("no")),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(delivery__order_deadline__gte=date.today())
        elif self.value() == "no":
            return queryset.exclude(delivery__order_deadline__gte=date.today())
        else:
            return queryset


class OrderItemInlineOpen(admin.TabularInline):
    model = OrderItem
    fields = ["product", "unit_price", "quantity", "amount"]
    readonly_fields = ["unit_price", "amount"]
    extra = 0

    @admin.display(description=_("unit price"))
    def unit_price(self, obj):
        p = obj.product
        return p.unit_price


class OrderItemInlineClosed(admin.TabularInline):
    model = OrderItem
    fields = ["product_name", "product_unit_price", "quantity", "amount"]
    readonly_fields = ["amount"]
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "delivery_link",
        "amount",
        "last_updated_date",
        "open",
    )
    list_filter = (OrderIsOpenFilter, "user", "delivery")
    readonly_fields = ["amount", "creation_date", "last_updated_date", "open"]
    inlines = [OrderItemInlineOpen, OrderItemInlineClosed]

    class Media:
        css = {"all": ("css/hide_admin_original.css",)}

    @admin.display(description=_("delivery"), ordering="delivery")
    def delivery_link(self, obj):
        d = obj.delivery
        d_admin_url = reverse("admin:baskets_delivery_change", args=[d.id])
        return format_html(f"<a href='{d_admin_url}'>{d.date}</a>")

    def get_queryset(self, request):
        """Add 'open_' to queryset for sorting 'open' field"""
        qs = super().get_queryset(request)
        qs = qs.annotate(
            open_=Case(
                When(delivery__order_deadline__gte=date.today(), then=True),
                default=False,
            )
        )
        return qs

    @admin.display(description=_("open"), boolean=True, ordering="open_")
    def open(self, obj):
        """Allow using @property as 'list_display' field"""
        return obj.is_open

    def get_formsets_with_inlines(self, request, obj=None):
        """Show OrderItemInlineOpen for new and opened orders, show OrderItemInlineClosed for closed ones"""
        order = obj

        # get 2 inlines
        open_inline = None
        closed_inline = None
        for inline in self.get_inline_instances(request, order):
            if isinstance(inline, OrderItemInlineOpen):
                open_inline = inline
            else:
                closed_inline = inline

        if not order or order.is_open:
            yield open_inline.get_formset(request, order), open_inline
        else:
            yield closed_inline.get_formset(request, order), closed_inline

    def delete_queryset(self, request, queryset):
        """Show message to contact deleted order users"""
        user_id_list = list(
            queryset.values_list("user__id", flat=True)
        )  # needs to convert into list, otherwise queryset will be empty after queryset.delete()
        queryset.delete()
        show_message_email_users(request, "", user_id_list)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "delivery", "product", "user", "quantity")
    list_editable = ("quantity",)
    list_filter = ("order__delivery", "product")

    @admin.display(description=_("delivery"))
    def delivery(self, obj):
        return obj.order.delivery

    @admin.display(description=_("user"), ordering="order__user")
    def user(self, obj):
        user = obj.order.user
        user_admin_url = reverse("admin:accounts_customuser_change", args=[user.id])
        return format_html(f"<a href='{user_admin_url}'>{user.username}</a>")

    def has_module_permission(self, request):
        """Don't show model on admin index"""
        return False

    def has_add_permission(self, request):
        """Don't show 'add' button"""
        return False

    # TODO: Fix custom OrderItem.save() not called on save
