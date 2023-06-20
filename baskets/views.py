from datetime import date

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.http import FileResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.views.generic import FormView
from rest_framework import viewsets

from .email import email_staff_contact
from .export import (
    get_order_forms_xlsx,
    get_orders_export_xlsx,
    get_producer_export_xlsx,
)
from .forms import ContactForm
from .models import Delivery, Order
from .serializers import (
    DeliverySerializer,
    DeliveryDetailSerializer,
    OrderSerializer,
    OrderDetailSerializer,
)


@login_required
def index(request):
    """Render 'Next Orders' page: a list of opened deliveries and its related orders in chronological order"""

    opened_deliveries = Delivery.objects.filter(
        order_deadline__gte=date.today()
    ).order_by("date")

    deliveries_orders = [
        {
            "delivery": d,
            "order": Order.objects.filter(user=request.user, delivery=d).first(),
        }
        for d in opened_deliveries
    ]

    return render(
        request,
        "baskets/index.html",
        {
            "title": "Commandes à venir",
            "deliveries_orders": deliveries_orders,
        },
    )


@login_required
def order_history(request):
    """Render 'Order history' page: a list of closed user orders in reverse chronological order"""

    closed_user_orders = Order.objects.filter(
        user=request.user, delivery__order_deadline__lt=date.today()
    ).order_by("-delivery__date")

    deliveries_orders = [
        {"delivery": o.delivery, "order": o} for o in closed_user_orders
    ]

    return render(
        request,
        "baskets/index.html",
        {"title": "Historique", "deliveries_orders": deliveries_orders},
    )


class ContactFormView(SuccessMessageMixin, FormView):
    """Contact admins:
    - GET: render 'Contact' page
    - POST: submit contact form to staff by email
    """

    template_name = "baskets/contact.html"
    form_class = ContactForm
    success_url = reverse_lazy("contact")
    success_message = "Votre message a été envoyé."

    def get_initial(self):
        initial = super().get_initial()
        initial["from_email"] = (
            self.request.user.email if self.request.user.is_authenticated else None
        )
        return initial

    def form_valid(self, form):
        email_staff_contact(
            from_email=form.cleaned_data["from_email"],
            subject=form.cleaned_data["subject"],
            message=form.cleaned_data["message"],
        )
        return super().form_valid(form)


class DeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    """Opened Deliveries API"""

    serializer_class = DeliverySerializer
    detail_serializer_class = DeliveryDetailSerializer
    queryset = Delivery.objects.filter(order_deadline__gte=date.today()).order_by(
        "date"
    )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return self.detail_serializer_class
        return super().get_serializer_class()


class OrderViewSet(viewsets.ModelViewSet):
    """User orders API"""

    serializer_class = OrderSerializer
    detail_serializer_class = OrderDetailSerializer

    def get_queryset(self):
        return self.request.user.orders.all().order_by("-delivery__date")

    def get_serializer_class(self):
        if self.action in ["retrieve", "create", "update"]:
            return self.detail_serializer_class
        return super().get_serializer_class()


@staff_member_required
def delivery_export(request, delivery_id):
    """Download delivery related orders forms"""

    # Attempt to retrieve delivery
    d = get_object_or_404(Delivery, id=delivery_id)

    buffer = get_order_forms_xlsx(d)
    return FileResponse(
        buffer, as_attachment=True, filename=f"{d.date}_bons_commande.xlsx"
    )


@staff_member_required
def order_export(request):
    """Download orders summary for accounting"""

    buffer = get_orders_export_xlsx()
    return FileResponse(buffer, as_attachment=True, filename="export_commandes.xlsx")


@staff_member_required
def producer_export(request):
    """Download summary of ordered products, one sheet per producer"""

    buffer = get_producer_export_xlsx()
    return FileResponse(buffer, as_attachment=True, filename="export_producteurs.xlsx")
