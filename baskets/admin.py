from datetime import date

from django.contrib import admin, messages
from django.contrib.auth.models import Group
from django.contrib.postgres.aggregates import StringAgg
from django.db.models import Count, Sum, Case, When
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .email import email_user_account_activated
from .models import User, Producer, Product, Delivery, Order, OrderItem


class MembershipInline(admin.TabularInline):
    model = Group.user_set.through
    readonly_fields = ["user"]
    extra = 0


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "groups_str", "is_active", "is_staff")
    fields = ("username", "first_name", "last_name", "email", "phone", "address", "groups",
              "is_active", "is_staff", "is_superuser", "date_joined", "last_login")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(groups_=StringAgg("groups__name", ", "))  # PostgreSQL specific aggregation function
        return qs

    @admin.display(description="groupe(s)", ordering="groups_")
    def groups_str(self, obj):
        return obj.groups_

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        # notify user when its account is activated
        user = obj
        if "is_active" in form.changed_data and user.is_active:
            email_user_account_activated(user)
            messages.add_message(
                request,
                messages.INFO,
                f"Un email a été envoyé à '{user}' pour lui notifier l'activation de son compte"
            )


def show_message_email_users(request, status_message, user_id_list):
    users = User.objects.filter(id__in=user_id_list)
    emails_str = ", ".join([user.email for user in users])
    messages.add_message(
        request,
        messages.SUCCESS,
        mark_safe(
            f"{status_message}."
            f"<br>Pour envoyer un email aux utilisateurs concernés "
            f"<a href='mailto:?bcc={emails_str}'>cliquez ici</a>"
        )
    )


class ProductInline(admin.TabularInline):
    model = Product
    fields = ["name", "unit_price"]
    ordering = ["name"]
    extra = 0

    def get_queryset(self, request):
        """override InlineModelAdmin method to filter queryset (not show inactive products)"""
        queryset = super().get_queryset(request)
        if not self.has_view_or_change_permission(request):
            queryset = queryset.none()
        return queryset.filter(is_active=True)


@admin.register(Producer)
class ProducerAdmin(admin.ModelAdmin):
    inlines = [ProductInline]

    class Media:
        css = {
            "all": ("baskets/css/hide_admin_original.css",)
        }
        js = ("baskets/js/admin_add_help_text_to_productinline.js",)

    def save_formset(self, request, form, formset, change):
        """If a product is deleted or if its unit_price changes, update related orders and show a message"""

        # from https://docs.djangoproject.com/en/3.2/ref/contrib/admin/#django.contrib.admin.ModelAdmin.save_formset
        products_new_or_updated = formset.save(commit=False)  # don't save them yet
        for product in formset.deleted_objects:
            if user_id_list := product.delete():
                show_message_email_users(
                    request,
                    f"Le produit « {product} » a été supprimé des commandes ouvertes",
                    user_id_list,
                )
        for product in products_new_or_updated:
            try:
                previous_price = Product.objects.get(pk=product.id).unit_price
                user_id_list = product.save()  # update product in DB and related opened order items
                if product.unit_price != previous_price and user_id_list:
                    show_message_email_users(
                        request,
                        f"Le produit « {product} » a été mis à jour dans les commandes ouvertes",
                        user_id_list,
                    )
            except Product.DoesNotExist:  # new product
                product.save()
        formset.save_m2m()

    def get_queryset(self, request):
        """Override ModelAdmin method to filter queryset (not show inactive producers)"""
        queryset = super().get_queryset(request)
        if not self.has_view_or_change_permission(request):
            queryset = queryset.none()
        return queryset.filter(is_active=True)

    def delete_queryset(self, request, queryset):
        """Override ModelAdmin method to force call of delete() method for each producer (do soft-delete)"""
        for producer in queryset:
            producer.delete()


class DeliveryProductInline(admin.TabularInline):
    model = Delivery.products.through
    verbose_name_plural = "Liste des quantités commandées par produit"
    readonly_fields = ["producer", "product", "total_ordered_quantity"]
    ordering = ["product__producer", "product__name"]
    extra = 0
    can_delete = False

    @admin.display(description="producteur")
    def producer(self, obj):
        return obj.product.producer

    @admin.display(description="quantité totale commandée")
    def total_ordered_quantity(self, obj):
        d = obj.delivery
        p = obj.product
        order_items = p.order_items.filter(order__delivery=d)
        total_quantity = order_items.aggregate(Sum("quantity"))["quantity__sum"]
        order_item_admin_url = reverse("admin:baskets_orderitem_changelist")
        modify_quantity_url = f"{order_item_admin_url}?order__delivery__id__exact={d.id}&product__id__exact={p.id}"

        if total_quantity:
            return format_html(f"{total_quantity} <a href='{modify_quantity_url}'>(Modifier)</a>")
        else:
            return 0

    def has_add_permission(self, request, obj):
        """Hide 'add' line at the bottom of inline"""
        return False


@admin.action(description="Envoyer email aux utilisateurs des livraisons selectionnées")
def mailto_users_from_deliveries(modeladmin, request, queryset):
    # TODO: merge with show_message_email_users?
    deliveries = queryset
    emails = [u.email for u in User.objects.filter(orders__delivery__in=deliveries).distinct()]
    emails_str = ", ".join(emails)
    messages.add_message(
        request,
        messages.INFO,
        mark_safe(f"<a href='mailto:?bcc={emails_str}'>Clic ici pour envoyer l'email</a>")
    )


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ("date", "orders_count", "export")
    ordering = ["-date"]
    filter_horizontal = ("products",)
    inlines = [DeliveryProductInline]
    actions = [mailto_users_from_deliveries]

    class Media:
        css = {
            "all": ("baskets/css/hide_admin_original.css",)
        }

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(Count("orders"))
        return qs

    @admin.display(description="nombre de commandes", ordering="orders__count")
    def orders_count(self, obj):
        delivery_orders_url = reverse("admin:baskets_order_changelist") + f"?delivery__id__exact={obj.id}"
        return format_html(
            f"<a href='{delivery_orders_url}'>{obj.orders__count}</a>"
        )

    @admin.display(description="exporter")
    def export(self, obj):
        d = obj
        delivery_export_url = reverse("baskets:delivery_export", args=[d.id])
        if d.orders.count() and not d.is_open:
            return format_html(
                f"<a href='{delivery_export_url}'>Exporter les bons de commande</a>"
            )
        else:
            return "-"

    def get_formsets_with_inlines(self, request, obj=None):
        """"Override method to hide inline on add view"""
        for inline in self.get_inline_instances(request, obj):
            # show inline if obj exists
            if obj is not None:
                yield inline.get_formset(request, obj), inline

    def save_model(self, request, obj, form, change):
        """If a product is removed from an opened delivery, show a message"""
        # opened order_items are deleted on delivery_product_removed() triggered by m2m_changed signal
        super().save_model(request, obj, form, change)

        d = obj
        if d.is_open and "products" in form.changed_data:
            previous_products_ids = [p.id for p in obj.products.all()]
            new_products_ids = [int(str_id) for str_id in form["products"].data]
            if removed_products_ids := set(previous_products_ids).difference(new_products_ids):
                if order_items := OrderItem.objects.filter(product__id__in=removed_products_ids, order__delivery=d):
                    products_html_list = "</li><li>".join(
                        [p.name for p in Product.objects.filter(id__in=removed_products_ids)]
                    )
                    user_id_list = [u.id for u in User.objects.filter(orders__items__in=order_items).distinct()]
                    show_message_email_users(
                        request,
                        f"Le(s) produit(s): <ul><li>{products_html_list}</li></ul>"
                        f"ont été supprimé(s) des commandes ouvertes",
                        user_id_list
                    )

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Override method to filter products"""
        if db_field.name == "products":
            kwargs["queryset"] = Product.objects.filter(is_active=True)  # not active hidden for all deliveries
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class OrderIsOpenFilter(admin.SimpleListFilter):
    """Add filter by order.is_open property"""
    title = "Ouverte"
    parameter_name = "open"

    def lookups(self, request, model_admin):
        return (
            ("Yes", "Oui"),
            ("No", "Non"),
        )

    def queryset(self, request, queryset):
        if self.value() == "Yes":
            return queryset.filter(delivery__order_deadline__gte=date.today())
        elif self.value() == "No":
            return queryset.exclude(delivery__order_deadline__gte=date.today())
        else:
            return queryset


class OrderItemInlineOpen(admin.TabularInline):
    model = OrderItem
    fields = ["product", "unit_price", "quantity", "amount"]
    readonly_fields = ["unit_price", "amount"]
    extra = 0

    @admin.display(description="prix unitaire")
    def unit_price(self, obj):
        p = obj.product
        return p.unit_price


class OrderItemInlineClosed(admin.TabularInline):
    model = OrderItem
    fields = ["saved_p_name", "saved_p_unit_price", "quantity", "amount"]
    readonly_fields = ["amount"]
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "delivery_link", "amount", "creation_date", "open")
    list_filter = (OrderIsOpenFilter, "user", "delivery")
    readonly_fields = ["amount", "creation_date", "open"]
    inlines = [OrderItemInlineOpen, OrderItemInlineClosed]

    class Media:
        css = {
            "all": ("baskets/css/hide_admin_original.css",)
        }

    @admin.display(description="livraison", ordering="delivery")
    def delivery_link(self, obj):
        d = obj.delivery
        d_admin_url = reverse("admin:baskets_delivery_change", args=[d.id])
        return format_html(
            f"<a href='{d_admin_url}'>{d.date}</a>"
        )

    def get_queryset(self, request):
        """add 'open_' to queryset for sorting 'open'"""
        qs = super().get_queryset(request)
        qs = qs.annotate(
            open_=Case(
                When(delivery__order_deadline__gte=date.today(), then=True),
                default=False
            )
        )
        return qs

    @admin.display(description="Ouverte", boolean=True, ordering="open_")
    def open(self, obj):
        """represent order.is_open property"""
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
        user_id_list = list(queryset.values_list("user__id", flat=True))
        queryset.delete()
        show_message_email_users(
            request,
            "Le(s) commande(s) ont été supprimée(s)",
            user_id_list,
        )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "delivery", "product", "user", "quantity")
    list_editable = ("quantity",)
    list_filter = ("order__delivery", "product")

    @admin.display(description="livraison")
    def delivery(self, obj):
        return obj.order.delivery

    @admin.display(description="utilisateur", ordering="order__user")
    def user(self, obj):
        user = obj.order.user
        user_admin_url = reverse("admin:baskets_user_change", args=[user.id])
        return format_html(
            f"<a href='{user_admin_url}'>{user.username}</a>"
        )

    def has_module_permission(self, request):
        """Don't show model on admin index"""
        return False

    def has_add_permission(self, request):
        """Don't show 'add' button"""
        return False

    def save_model(self, request, obj, form, change):
        if "quantity" in form.changed_data:
            order = obj.order
            user = obj.order.user
            order_admin_url = reverse("admin:baskets_order_change", args=[order.id])
            messages.add_message(
                request,
                messages.WARNING,
                mark_safe(
                    f"La <a href='{order_admin_url}'>commande</a> de {user} a été modifiée, pensez à prévenir "
                    f"l'utilisateur: <a href='mailto:{user.email}'>{user.email}</a>, "
                    f"<a href='tel:{user.phone}'>{user.phone}</a>"
                )
            )
        super().save_model(request, obj, form, change)

    def delete_queryset(self, request, queryset):
        """Show a message to contact deleted items users"""
        user_id_list = list(queryset.values_list("order__user__id", flat=True))
        queryset.delete()
        show_message_email_users(
            request,
            "Le(s) ligne(s) de commande ont été supprimées",
            user_id_list,
        )


# Custom Group admin
admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("name", "members_count", "email")
    exclude = ("permissions",)
    inlines = [MembershipInline]

    class Media:
        css = {
            "all": ("baskets/css/hide_admin_original.css",)
        }

    @admin.display(description="nombre de membres")
    def members_count(self, obj):
        return obj.user_set.count()

    @staticmethod
    def email(obj):
        group_users = obj.user_set.all()
        emails = [user.email for user in group_users]
        emails_str = ", ".join(emails)
        return format_html(
            f"<a href='mailto:?bcc={emails_str}'>envoyer un email au groupe {obj.name}</a>"
        )
