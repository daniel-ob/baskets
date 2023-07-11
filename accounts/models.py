from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from config.settings import FR_PHONE_REGEX


class CustomUser(AbstractUser):
    # make first_name/last_name mandatory
    first_name = models.CharField(_("first name"), max_length=150, blank=False)
    last_name = models.CharField(_("last name"), max_length=150, blank=False)

    # add new fields
    phone = models.CharField(
        _("phone"), validators=[FR_PHONE_REGEX], max_length=18, blank=True
    )
    address = models.CharField(_("address"), max_length=128, blank=True)

    class Meta:
        verbose_name = _("user")
        ordering = ["username"]

    def __str__(self):
        return self.email or self.username
