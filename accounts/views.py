from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import UpdateView

from accounts.forms import CustomUserForm


class ProfileView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = get_user_model()
    form_class = CustomUserForm
    template_name = "account/profile.html"
    success_url = reverse_lazy("profile")
    success_message = _("Your details have been updated")

    def get_object(self):
        return self.request.user
