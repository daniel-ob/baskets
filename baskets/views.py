from datetime import date

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView
from rest_framework import viewsets

from .email import email_staff_contact
from .export import (
    get_order_forms_xlsx,
    get_orders_export_xlsx,
    get_producer_export_xlsx,
)
from .forms import ContactForm
from .models import Delivery
from .serializers import (
    DeliveryDetailSerializer,
    DeliverySerializer,
    OrderDetailSerializer,
    OrderSerializer,
)


class IndexPageView(LoginRequiredMixin, TemplateView):
    """Render 'Next Orders' page: a list of opened deliveries and its related orders in chronological order"""

    template_name = "baskets/index.html"

    def get_context_data(self, **kwargs):
        opened_deliveries = Delivery.objects.filter(
            order_deadline__gte=date.today()
        ).order_by("date")

        return {
            "title": "Commandes à venir",
            "deliveries_orders": [
                {
                    "delivery": d,
                    "order": d.orders.filter(user=self.request.user).first(),
                }
                for d in opened_deliveries
            ],
        }


class OrderHistoryPageView(LoginRequiredMixin, TemplateView):
    """Render 'Order history' page: a list of closed user orders in reverse chronological order"""

    template_name = "baskets/index.html"

    def get_context_data(self, **kwargs):
        closed_user_orders = self.request.user.orders.filter(
            delivery__order_deadline__lt=date.today()
        ).order_by("-delivery__date")

        deliveries_orders = [
            {"delivery": o.delivery, "order": o} for o in closed_user_orders
        ]

        return {"title": "Historique", "deliveries_orders": deliveries_orders}


class ContactPageView(SuccessMessageMixin, FormView):
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


def _prepare_excel_http_headers(filename):
    return {
        "Content-Type": "application/vnd.ms-excel",
        "Content-Disposition": f"attachment; filename={filename}",
    }


@staff_member_required
def delivery_export(request, delivery_id):
    """Download delivery related orders forms"""

    d = get_object_or_404(Delivery, id=delivery_id)

    return HttpResponse(
        get_order_forms_xlsx(d),
        headers=_prepare_excel_http_headers(f"{d.date}_bons_commande.xlsx"),
    )


@staff_member_required
def order_export(request):
    """Download summary of user order amounts per month"""

    return HttpResponse(
        get_orders_export_xlsx(),
        headers=_prepare_excel_http_headers("export_commandes.xlsx"),
    )


@staff_member_required
def producer_export(request):
    """Download summary of ordered product quantities per month, one sheet per producer"""

    return HttpResponse(
        get_producer_export_xlsx(),
        headers=_prepare_excel_http_headers("export_producteurs.xlsx"),
    )
