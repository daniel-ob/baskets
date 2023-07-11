from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class BasketsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'baskets'
    verbose_name = _('Baskets')
