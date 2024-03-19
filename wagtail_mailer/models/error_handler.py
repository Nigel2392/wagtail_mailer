from django.db import models
from django.conf import settings
from django.forms import ValidationError
from django.utils.translation import gettext_lazy as _
from wagtail.contrib.settings.models import register_setting
from wagtail.contrib.settings.models import BaseGenericSetting
from wagtail.admin.panels import FieldPanel, InlinePanel

from django.db import models
from modelcluster.models import ClusterableModel
from modelcluster.fields import ParentalKey
from wagtail.models import Orderable
from wagtail.fields import (
    StreamField,
    StreamValue,
)
from wagtail import blocks


from .mailer import Mailer
from ..tasks import send_mail_task

class StatusCodeRangeBlock(blocks.StructBlock):
    
    start = blocks.IntegerBlock(
        required=True,
        min_value=100,
        max_value=599,
        default=400,
        help_text=_("The start of the status code range.")
    )
    end = blocks.IntegerBlock(
        required=True,
        min_value=100,
        max_value=599,
        default=599,
        help_text=_("The end of the status code range.")
    )

    def clean(self, value):
        if value["start"] > value["end"]:
            raise ValidationError(_("The start of the range must be less than the end."))
        return super().clean(value)

class ExceptionReceiver(Orderable):

    settings = ParentalKey(
        "wagtail_mailer.ExceptionMailSettings",
        on_delete=models.CASCADE,
        related_name="exception_receivers",
    )

    email = models.EmailField(
        max_length=255,
        blank=False,
        null=False,
        help_text=_("The email address to send emails to"),
    )

    description = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_("A description of the user, or their occupation within the company.")
    )

    class Meta:
        verbose_name = _("Exception Receiver")
        verbose_name_plural = _("Exception Receivers")

@register_setting(
    name="error_email_settings",
)
class ExceptionMailSettings(ClusterableModel, BaseGenericSetting):

    mailbox = models.ForeignKey(
        Mailer,
        verbose_name=_("Mailbox"),
        help_text=_("The mailbox to send exception emails from"),
        related_name="exception_mail_settings",
        on_delete=models.CASCADE,
        null=True,
        blank=False,
    )

    status_code_ranges: StreamValue = StreamField([
            ("status_code_range", StatusCodeRangeBlock())
        ],
        use_json_field=True,
        blank=True,
        null=True,
    )

    panels = [
        FieldPanel("mailbox"),
        FieldPanel("status_code_ranges"),
        InlinePanel("exception_receivers", label=_("Exception Receivers")),
    ]

    class Meta:
        verbose_name = _("Exception Mail Settings")
        verbose_name_plural = _("Exception Mail Settings")

    @property
    def status_codes(self):
        for block in self\
            .status_code_ranges\
                .blocks_by_name("status_code_range"):
            
            start = block.value["start"]
            end = block.value["end"]
            yield start, end

    @property
    def has_codes(self) -> bool:
        return self.status_code_ranges and len(self.status_code_ranges) > 0

    def in_range(self, status_code: int) -> bool:
        for start, end in self.status_codes:
            if start <= status_code <= end:
                return True
        return False

    @classmethod
    def mail_admins(cls, 
        subject,
        message,
        html_message=None,
        fail_silently=False,
        request_or_site=None):

        if not cls.objects.exists():
            return
        
        if request_or_site is None:
            self = cls.objects.first()
        else:
            self = cls.load(request_or_site=request_or_site)

        if not self.mailbox:
            return -1
        
        receivers = self.exception_receivers.all()
        if not receivers.exists():
            return -2
        
        recipients = list(receivers.values_list("email", flat=True))

        settings_recipients = getattr(settings, "ADMINS", [])
        if settings_recipients:
            recipients += [tup[1] for tup in settings_recipients]

        recipients = list(set(recipients))

        return send_mail_task.delay(
            mailbox_pk=self.mailbox.pk,
            subject=subject,
            message=message,
            recipient_list=recipients,
            html_message=html_message,
            fail_silently=fail_silently,
            notify_admins=False,
        )