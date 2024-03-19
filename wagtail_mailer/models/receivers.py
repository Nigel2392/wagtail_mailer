from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

from wagtail.admin.panels import FieldPanel, FieldRowPanel
from modelcluster.fields import ParentalKey
from wagtail.models import Orderable

class BaseUserReceiver(models.Model):
    user = models.ForeignKey(
        get_user_model(),
        verbose_name=_("User"),
        on_delete=models.SET_NULL,
        related_name="+",
        blank=True,
        null=True,
        help_text=_("The user associated with the email address")
    )
    receives_mail = models.BooleanField(
        default=True,
        help_text=_("Whether or not the email address receives emails")
    )

    panels = [
        FieldPanel("user"),
        FieldPanel("receives_mail"),
    ]

    class Meta:
        abstract = True
        verbose_name = _("User Receiver")
        verbose_name_plural = _("User Receivers")

class BaseReceiver(BaseUserReceiver):
    email_required = True
    email = models.EmailField(
        max_length=255,
        blank=email_required,
        null=email_required,
        help_text=_("The email address to send emails to"),
        unique=True
    )

    first_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_("The first name of the email recipient")
    )

    last_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_("The last name of the email recipient")
    )

    panels = BaseUserReceiver.panels + [
        FieldPanel("email"),
        FieldRowPanel([
            FieldPanel("first_name"),
            FieldPanel("last_name"),
        ], heading=_("Name")),
    ]

    class Meta:
        abstract = True
        verbose_name = _("Receiver")
        verbose_name_plural = _("Receivers")

    def __str__(self):
        return f"{self.email}"
    
class Receiver(BaseReceiver):
    class Meta:
        verbose_name = _("Receiver")
        verbose_name_plural = _("Receivers")

class AdminReceiver(Orderable, BaseReceiver):

    email_required = False
    mailbox = ParentalKey(
        "wagtail_mailer.Mailer",
        verbose_name=_("Mailbox"),
        related_name="admin_receivers",
        on_delete=models.CASCADE,
    )

    panels = BaseReceiver.panels + [
        FieldPanel("mailbox"),
    ]

    def __str__(self):
        return f"{self.email or self.user} ({self.mailbox})"

    class Meta:
        verbose_name = _("Admin Receiver")
        verbose_name_plural = _("Admin Receivers")
