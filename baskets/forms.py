from django.forms import CharField, EmailField, Form, Textarea, TextInput
from django.utils.translation import gettext_lazy as _


class ContactForm(Form):
    from_email = EmailField(
        required=True,
        widget=TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Email"),
                "autocomplete": "email",
            }
        ),
    )
    subject = CharField(
        required=True,
        widget=TextInput(attrs={"class": "form-control", "placeholder": _("Subject")}),
    )
    message = CharField(
        required=True,
        widget=Textarea(
            attrs={"class": "form-control", "rows": 6, "placeholder": _("Your message")}
        ),
    )
