from django.urls import path
from django.views.i18n import JavaScriptCatalog

from . import views


urlpatterns = [
    path("", views.IndexPageView.as_view(), name="index"),  # 'next orders' page
    path("history/", views.OrderHistoryPageView.as_view(), name="order_history"),
    path("contact/", views.ContactPageView.as_view(), name="contact"),

    # Staff exports
    path(
        "deliveries/<int:delivery_id>/export",
        views.delivery_export,
        name="delivery_export",
    ),
    path("orders/export", views.order_export, name="order_export"),
    path("producers/export", views.producer_export, name="producer_export"),

    # Javascript internationalization
    path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
]
