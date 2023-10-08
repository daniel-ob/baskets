from datetime import date

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView, TemplateView

from .email import email_staff
from .forms import ContactForm
from .models import Delivery


class IndexPageView(LoginRequiredMixin, TemplateView):
    """Render 'Next Orders' page: a list of opened deliveries and its related orders in chronological order"""

    template_name = "baskets/orders.html"

    def get_context_data(self, **kwargs):
        opened_deliveries = Delivery.objects.filter(
            order_deadline__gte=date.today()
        ).order_by("date")

        return {
            "title": _("Next orders"),
            "deliveries_orders": [
                {
                    "delivery": d,
                    "order": d.orders.filter(user=self.request.user).first(),
                }
                for d in opened_deliveries
            ],
        }


class OrderHistoryPageView(LoginRequiredMixin, TemplateView):
    template_name = "baskets/orders.html"

    def get_context_data(self, **kwargs):
        closed_user_orders = self.request.user.orders.filter(
            delivery__order_deadline__lt=date.today()
        ).order_by("-delivery__date")

        deliveries_orders = [
            {"delivery": o.delivery, "order": o} for o in closed_user_orders
        ]

        return {"title": _("Order history"), "deliveries_orders": deliveries_orders}


class ContactPageView(SuccessMessageMixin, FormView):
    template_name = "baskets/contact.html"
    form_class = ContactForm
    success_url = reverse_lazy("contact")
    success_message = _("Your message have been sent")

    def get_initial(self):
        initial = super().get_initial()
        initial["from_email"] = (
            self.request.user.email if self.request.user.is_authenticated else None
        )
        return initial

    def form_valid(self, form):
        email_staff(
            from_email=form.cleaned_data["from_email"],
            subject=form.cleaned_data["subject"],
            message=form.cleaned_data["message"],
        )
        return super().form_valid(form)
