from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import BasketsPasswordResetForm, BasketsSetPasswordForm

app_name = "baskets"
urlpatterns = [
    path("", views.index, name="index"),  # 'next orders' page
    path("history/", views.order_history, name="order_history"),

    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register, name="register"),

    # Password reset. Use default auth_views with custom templates and forms
    path("password_reset/",
         auth_views.PasswordResetView.as_view(
             template_name="baskets/password/password_reset.html",
             form_class=BasketsPasswordResetForm),
         name="password_reset"),
    path("password_reset/done/",
         auth_views.PasswordResetDoneView.as_view(
             template_name="baskets/password/password_reset_done.html"),
         name="password_reset_done"),
    path("reset/<uidb64>/<token>/",
         auth_views.PasswordResetConfirmView.as_view(
             template_name="baskets/password/password_reset_confirm.html",
             form_class=BasketsSetPasswordForm),
         name="password_reset_confirm"),
    path("reset/done/",
         auth_views.PasswordResetCompleteView.as_view(
             template_name="baskets/password/password_reset_complete.html"),
         name="password_reset_complete"),

    path("profile/", views.profile, name="profile"),
    path("contact/", views.contact, name="contact"),

    # API Routes
    path("orders", views.orders, name="orders"),
    path("orders/<int:order_id>", views.order, name="order"),
    path("deliveries", views.deliveries, name="deliveries"),
    path("deliveries/<int:delivery_id>", views.delivery, name="delivery"),

    # Staff exports
    path("deliveries/<int:delivery_id>/export", views.delivery_export, name="delivery_export"),
    path("orders/export", views.order_export, name="order_export"),
    path("producers/export", views.producer_export, name="producer_export"),
]
