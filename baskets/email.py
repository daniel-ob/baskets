from django.apps import apps
from django.conf import settings
from django.core.mail import EmailMessage
from django.template import loader
from django.urls import reverse

from baskets.models import User

app_name = apps.get_app_config("baskets").verbose_name


def email_staff_ask_account_activation(user):
    """Send email to staff members to ask for user account activation"""

    user_admin_url = settings.SERVER_URL + reverse("admin:baskets_user_change", args=[user.id])
    message = loader.render_to_string("baskets/account_validation_email.html", {
        "username": user.username,
        "user_admin_url": user_admin_url,
    })
    email = EmailMessage(
        subject=f"[{app_name}] Nouvel utilisateur {user.username}",
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[staff.email for staff in User.objects.filter(is_staff=True)],
    )
    email.send()


def email_staff_contact(from_email, subject, message):
    """Send email to staff with 'Contact' form data"""

    email = EmailMessage(
        subject=f"[{app_name}] Contact: {subject}",
        body=f"Message de {from_email}:\n{message}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[staff.email for staff in User.objects.filter(is_staff=True)],
        reply_to=[from_email],
    )
    email.send()


def email_user_account_activated(user):
    """Send email to user to notify its account activation"""

    message = loader.render_to_string("baskets/account_activated_email.html", {
        "username": user.username,
        "index_url": settings.SERVER_URL + reverse("baskets:index")
    })
    email = EmailMessage(
        subject=f"[{app_name}] Bienvenue",
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    email.send()
