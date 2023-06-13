from allauth.account.forms import (
    SignupForm,
    LoginForm,
    ResetPasswordForm,
    ResetPasswordKeyForm,
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


class CustomResetPasswordForm(ResetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_widgets_attrs(self.fields)


class CustomResetPasswordKeyForm(ResetPasswordKeyForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_widgets_attrs(self.fields)
