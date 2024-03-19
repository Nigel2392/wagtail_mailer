from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup
from wagtail.snippets.models import register_snippet
from wagtail.contrib.settings.registry import SettingMenuItem
from .models import (
    Mailer,
    Receiver,
    AdminReceiver,
    ExceptionMailSettings,
)
from django.utils.translation import gettext_lazy as _


from .actions import *

# Register your models here.
class MailerAdmin(SnippetViewSet):
    model = Mailer
    menu_label = _("Mailservers")
    icon = "key"
    menu_order = -90
    list_display = (
        "email_host",
        "email_port",
        "emails_sent",
        "email_use_display",
        "email_timeout",
        "email_fail_silently",
    )
    search_fields = (
        "email_host",
        "email_port",
    )

class ReceiverAdmin(SnippetViewSet):
    model = Receiver
    menu_label = _("Mail Receivers")
    icon = "group"
    menu_order = -100
    list_display = ("email", "first_name", "last_name",)
    search_fields = ("email", "first_name", "last_name",)

class AdminReceiverAdmin(SnippetViewSet):
    model = AdminReceiver
    menu_label = _("Admin Mail Receivers")
    icon = "user"
    menu_order = -100
    list_display = ("user","email", "first_name", "last_name",)
    search_fields = ("user","email", "first_name", "last_name",)

class EmailAdminGroup(SnippetViewSetGroup):
    menu_label = _("Emails")
    menu_name = "email"
    menu_icon = "mail"
    menu_order = 200
    add_to_admin_menu = False
    add_to_settings_menu = True

    items = [
        MailerAdmin,
        ReceiverAdmin,
        AdminReceiverAdmin,
    ]

    def get_submenu_items(self):
        return super().get_submenu_items() + [
            SettingMenuItem(
                model=ExceptionMailSettings,
                name="error_email_settings",
                icon="error",
            ),
        ]


register_snippet(EmailAdminGroup)


@hooks.register("construct_settings_menu")
def change_settings_menu(request, items):
    items[:] = [item for item in items if item.name != "error_email_settings"]
    return items

