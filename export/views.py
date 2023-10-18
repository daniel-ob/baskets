from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from baskets.models import Delivery

from .base import get_order_forms_xlsx, get_orders_export_xlsx, get_producer_export_xlsx


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
        headers=_prepare_excel_http_headers(f"{d.date}_order_forms.xlsx"),
    )


@staff_member_required
def order_export(request):
    """Download summary of user order amounts per month"""

    return HttpResponse(
        get_orders_export_xlsx(),
        headers=_prepare_excel_http_headers("order_export.xlsx"),
    )


@staff_member_required
def producer_export(request):
    """Download summary of ordered product quantities per month, one sheet per producer"""

    return HttpResponse(
        get_producer_export_xlsx(),
        headers=_prepare_excel_http_headers("producer_export.xlsx"),
    )
