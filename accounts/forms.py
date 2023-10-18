from allauth.account.forms import (
    LoginForm,
    ResetPasswordForm,
    ResetPasswordKeyForm,
    SignupForm,
)
from django.forms import ModelForm

from accounts.models import CustomUser


def update_widgets_attrs(fields):
    for field in fields.values():
        field.widget.attrs["placeholder"] = field.label
        field.widget.attrs["class"] = "form-control"


class CustomLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_widgets_attrs(self.fields)


class CustomUserForm(ModelForm):
    """User form for 'Signup' and 'Profile' pages"""

    class Meta:
        model = CustomUser
        fields = ["email", "first_name", "last_name", "phone", "address"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_widgets_attrs(self.fields)


class CustomSignupForm(SignupForm, CustomUserForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_widgets_attrs(self.fields)

    def custom_signup(self, request, user):
        # save user additional fields
        user.phone = self.cleaned_data["phone"]
        user.address = self.cleaned_data["address"]
        user.save()


class CustomResetPasswordForm(ResetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_widgets_attrs(self.fields)


class CustomResetPasswordKeyForm(ResetPasswordKeyForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_widgets_attrs(self.fields)
