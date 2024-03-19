from typing import Any
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.html import strip_tags
from django.core.files import File
from django.core.mail import get_connection
from django import forms

from wagtail.contrib.settings.context_processors import SettingProxy
from wagtail.contrib.settings.models import BaseSiteSetting
from wagtail.admin.panels import FieldPanel, FieldRowPanel, InlinePanel, ObjectList, TabbedInterface
from ..tasks import send_mass_mail_task, send_mail_task, send_mail_alternative_task
from ..mailing import (
    send_mail as django_send_mail, 
    send_mass_mail as django_send_mass_mail,
    FileDescriptor
)

from email.headerregistry import Address

from django.db import models
from django.template import engines, Template, TemplateSyntaxError
from modelcluster.models import ClusterableModel


# https://stackoverflow.com/questions/2167269/load-template-from-a-string-instead-of-from-a-file
def template_from(getter_name: str, template: str, using=None) -> Template:
    """
    Load a template from a file or a string,
    using a given template engine or using the default backends 
    from settings.TEMPLATES if no engine was specified.

    """
    # This function is based on django.template.loader.get_template, 
    chain = []
    engine_list = engines.all() if using is None else [engines[using]]
    for engine in engine_list:
        try:
            fn = getattr(engine, getter_name)
            if fn is None:
                raise AttributeError(f"{engine} does not support loading templates from '{getter_name}'")
            return fn(template)
        
        except TemplateSyntaxError as e:
            chain.append(e)
    raise TemplateSyntaxError(template, chain)


class PasswordField(models.CharField):
    def formfield(self, **kwargs: Any) -> Any:
        kwargs["widget"] = forms.TextInput(
            attrs={"type": "password", "autocomplete": "new-password"}
        )
        return super().formfield(**kwargs)


class Mailer(ClusterableModel):
    emails_sent = models.IntegerField(
        default=0,
        editable=False,
        help_text=_("The number of emails sent")
    )

    email_host = models.CharField(
        null=False,
        blank=False,
        max_length=255,
        help_text=_("The email host")
    )

    email_port = models.IntegerField(
        null=False,
        blank=False,
        default=587,
        help_text=_("The email port")
    )

    email_host_user = models.EmailField(
        max_length=255,
        blank=False,
        null=True,
        help_text=_("The email host user")
    )

    email_host_password = PasswordField(
        max_length=255,
        blank=False,
        null=True,
        help_text=_("The email host password")
    )

    class EMAIL_USE_CHOICES(models.TextChoices):
        TLS = "1", _("TLS")
        SSL = "2", _("SSL")
        NONE = "3", _("NONE")

    email_use = models.CharField(
        max_length=255,
        choices=EMAIL_USE_CHOICES.choices,
        default=EMAIL_USE_CHOICES.NONE,
        help_text=_("The email use")
    )

    email_timeout = models.IntegerField(
        default=60,
        help_text=_("The email timeout in seconds")
    )

    email_fail_silently = models.BooleanField(
        default=False,
        help_text=_("Fail silently")
    )

    configuration_panels = [
        FieldPanel("emails_sent", read_only=True),
        FieldRowPanel([
            FieldPanel("email_host"),
            FieldPanel("email_port"),
        ], heading=_("Email Host")),
        FieldRowPanel([
            FieldPanel("email_host_user"),
            FieldPanel("email_host_password", widget=forms.widgets.Input(attrs={"type": "password"}), permission=["change_password"]),
        ], heading=_("Email Host Credentials")),
        FieldRowPanel([
            FieldPanel("email_use"),
            FieldPanel("email_timeout"),
            FieldPanel("email_fail_silently"),
        ], heading=_("Email Options")),
    ]

    admin_email_panels = [
        InlinePanel("admin_receivers", label=_("Admin Receivers")),
    ]

    edit_handler = TabbedInterface([
        ObjectList(configuration_panels, heading=_("Configuration")),
        ObjectList(admin_email_panels, heading=_("Admin Emails")),
    ])

    class Meta:
        verbose_name = _("Mail Server")
        verbose_name_plural = _("Mail Servers")
        permissions = [
            ("edit_server_password", _("Can edit server password")),
        ]

    def __init__(self, *args, **kwargs):
        self._connection = None
        super().__init__(*args, **kwargs)

    @property
    def email_use_display(self):
        if self.email_use == self.EMAIL_USE_CHOICES.TLS:
            return "TLS"
        elif self.email_use == self.EMAIL_USE_CHOICES.SSL:
            return "SSL"
        else:
            return "NONE"

    @property
    def use_ssl(self):
        return self.email_use == self.EMAIL_USE_CHOICES.SSL
    
    @property
    def use_tls(self):
        return self.email_use == self.EMAIL_USE_CHOICES.TLS

    def __str__(self) -> str:
        if not self.email_host:
            return "Misconfigured"
        try:
            addr = Address(addr_spec=self.email_host_user)
        except:
            return f"{self.email_host}:{self.email_port}"
        return f"{addr.username}@{self.email_host}:{self.email_port}"   

    def get_connection(self, fail_silently=False):
        if self._connection:
            return self._connection
        self._connection = get_connection(
            host = self.email_host,
            port = self.email_port,
            username = self.email_host_user,
            password = self.email_host_password,
            use_tls  = self.use_tls,
            use_ssl = self.use_ssl,
            timeout = self.email_timeout,
            fail_silently=fail_silently,
        )
        return self._connection

    def send_mail(self, subject, message, recipient_list, html_message=None, notify_admins=False) -> int:
        """Sends a single email message to a recipient list."""
        if not recipient_list:
            return 0
        return send_mail_task.delay(self.pk,
                                    subject,
                                    message,
                                    recipient_list,
                                    html_message,
                                    fail_silently=self.email_fail_silently,
                                    notify_admins=notify_admins)
    
    def sync_send_mail(self, subject, message, recipient_list, html_message=None, notify_admins=False) -> int:
        """Sends a single email message to a recipient list."""
        if not recipient_list:
            return 0
        return django_send_mail(
            mailbox=self,
            subject=subject,
            message=message,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=self.email_fail_silently,
            notify_admins=notify_admins,
        )
    
    def send_mass_mail(self, datatuple, notify_admins=False):
        """
        Given a datatuple of (subject, message, from_email, recipient_list), send
        each message to each recipient list. Return the number of emails sent.
        Note: The API for this method is frozen. New code wanting to extend the
        functionality should use the EmailMessage class directly.
        """
        return send_mass_mail_task.delay(mailbox_pk=self.pk, datatuple=datatuple, fail_silently=self.email_fail_silently)
    
    
    def sync_mass_mail(self, datatuple, notify_admins=False):
        return django_send_mass_mail(
            mailbox=self,
            datatuple=datatuple,
            fail_silently=self.email_fail_silently,
            notify_admins=notify_admins,
        )
    
    def send_mail_alternative(self, 
            subject:                        str = "",
            body:                           str = "",
            to:                       list[str] = None,
            bcc:                      list[str] = None,
            attachments:             list[File] = None,
            headers:             dict[str, str] = None,
            alternatives: list[tuple[str, str]] = None,
            cc:                       list[str] = None,
            reply_to:                 list[str] = None,
            fail_silently                       = True,
            zipname                             = "attachments.zip",
        ) -> int:
        """Sends a single email message to a recipient list."""

        if attachments:
            attachments = FileDescriptor.from_files(*attachments, zipname=zipname).to_json()

        return send_mail_alternative_task.delay(
            subject=subject,
            body=body,
            to=to,
            bcc=bcc,
            attachments=attachments,
            headers=headers,
            alternatives=alternatives,
            cc=cc,
            reply_to=reply_to,
            fail_silently=fail_silently,
            mailbox_pk=self.pk,
        )

    def send_mail_template(self, subject, template_name, context, recipient_list, is_file=True, as_html=True, request=None, **mail_alternative_kwargs) -> int:
        """Sends a single email message to a recipient list."""
        if not recipient_list:
            return 0
        if is_file:
            tpl = template_from("get_template", template_name)
        else:
            tpl = template_from("from_string", template_name)

        if "email_message" not in context:
            context["email_message"] = {
                "subject": subject,
                "recipient_list": recipient_list,
            }

        if "settings" not in context and request is not None:
            context["settings"] = SettingProxy(request)
            context["request"] = request

        if as_html:
            html_message = tpl.render(context, request=request)
            message = strip_tags(html_message)
        else:
            html_message = None
            message = tpl.render(context, request=request)

        return self.send_mail_alternative(
            subject=subject,
            body=message,
            to=recipient_list,
            alternatives=[(html_message, "text/html")] if html_message else None,
            **mail_alternative_kwargs
        )
    

