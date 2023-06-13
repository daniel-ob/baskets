from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage


def email_staff_contact(from_email, subject, message):
    """Send email to staff with 'Contact' form data"""

    app_name = apps.get_app_config("baskets").verbose_name
    email = EmailMessage(
        subject=f"[{app_name}] Contact: {subject}",
        body=f"Message de {from_email}:\n{message}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[staff.email for staff in get_user_model().objects.filter(is_staff=True)],
        reply_to=[from_email],
    )
    email.send()
