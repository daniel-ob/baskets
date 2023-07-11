from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage
from django.utils.translation import gettext_lazy as _


def email_staff_contact(from_email, subject, message):
    """Send email to staff with 'Contact' form data"""

    app_name = apps.get_app_config("baskets").verbose_name
    body_text = _("Message from")
    email = EmailMessage(
        subject=f"[{app_name}] Contact: {subject}",
        body=f"{body_text} {from_email}:\n{message}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=get_user_model()
        .objects.filter(is_staff=True)
        .values_list("email", flat=True),
        reply_to=[from_email],
    )
    email.send()
