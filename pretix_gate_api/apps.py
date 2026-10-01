from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PretixGateApiPlugin(AppConfig):
    name = "pretix_gate_api"
    verbose_name = _("Pretix Gate API")

    class PretixPluginMeta:
        name = _("Pretix Gate API")
        author = "Thies Mueller"
        version = "0.0.1"
        category = "API"
        compatibility = "pretix>=2026.1"
        description = _(
            "Provides a custom API for reading and changing device gate assignments."
        )
        visible = True
        restricted = False
        featured = False
        level = "organizer"

        settings_links = []
        navigation_links = []