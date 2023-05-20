from django.contrib.auth import password_validation
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.forms import ModelForm, Form, TextInput, EmailField, EmailInput, CharField, PasswordInput, Textarea
from django.utils.translation import gettext_lazy as _

from .models import User


class UserForm(ModelForm):
    """User form for 'Register' and 'Profile' pages"""

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "phone", "address"]
        widgets = {
            "username": TextInput(attrs={"class": "form-control", "placeholder": "Nom d'utilisateur"}),
            "first_name": TextInput(attrs={"class": "form-control", "placeholder": "Prénom"}),
            "last_name": TextInput(attrs={"class": "form-control", "placeholder": "Nom"}),
            "email": TextInput(attrs={"class": "form-control", "placeholder": "Email"}),
            "phone": TextInput(attrs={"class": "form-control", "placeholder": "Téléphone"}),
            "address": TextInput(attrs={"class": "form-control", "placeholder": "Adresse"}),
        }


class BasketsPasswordResetForm(PasswordResetForm):
    """Extends default PasswordResetForm to customize email widget attributes"""

    email = EmailField(
        label="",
        max_length=254,
        widget=EmailInput(attrs={"class": "form-control",
                                 "placeholder": _("Email"),
                                 "autocomplete": "email",
                                 "autofocus": ""})
    )


class BasketsSetPasswordForm(SetPasswordForm):
    """Extends default SetPasswordForm to customize passwords widgets attributes"""

    new_password1 = CharField(
        widget=PasswordInput(attrs={"class": "form-control",
                                    "placeholder": _("New password"),
                                    "autocomplete": "new-password"}),
        strip=False,
        help_text=password_validation.password_validators_help_text_html(),
    )
    new_password2 = CharField(
        strip=False,
        widget=PasswordInput(attrs={"class": "form-control",
                                    "placeholder": _("New password confirmation"),
                                    "autocomplete": "new-password"}),
    )


class ContactForm(Form):
    from_email = EmailField(
        required=True,
        widget=TextInput(attrs={"class": "form-control", "placeholder": "Votre email", "autocomplete": "email"})
    )
    subject = CharField(
        required=True,
        widget=TextInput(attrs={"class": "form-control", "placeholder": "Objet"})
    )
    message = CharField(
        required=True,
        widget=Textarea(attrs={"class": "form-control", "rows": 6, "placeholder": "Votre message"})
    )
