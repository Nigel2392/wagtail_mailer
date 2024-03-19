from django.utils.log import AdminEmailHandler
from django.apps import apps
import logging

_MODEL_CLASS = None

def get_model_class():
    global _MODEL_CLASS
    if not _MODEL_CLASS:
        from .models import (
            ExceptionMailSettings,
        )
        _MODEL_CLASS = ExceptionMailSettings
    return _MODEL_CLASS

class WagtailSettingsEmailFilter(logging.Filter):
    def filter(self, record):
        if apps.ready:
            klass = get_model_class()
            settings = klass.load()
            if not settings:
                return True

            status_code = getattr(record, "status_code", None)
            if status_code:
                if settings.has_codes:
                    if status_code and not settings.in_range(status_code):
                        return True
                    return False
                
                # 503: Service Unavailable
                # The server is currently unavailable (because it is overloaded or down for maintenance, likely the latter).
                # We do not want to send emails for 503 errors.
                return 500 <= status_code < 600\
                and status_code != 503
        
        return True


class WagtailSettingsAdminEmailHandler(AdminEmailHandler):

    def send_mail(self, subject, message, *args, **kwargs):

        if not apps.ready:
            return

        klass = get_model_class()

        settings = klass.objects.all()
        if not settings.exists():
            return super().send_mail(subject, message, *args, **kwargs)
        
        setting = settings.first()
        if not setting.mailbox:
            return super().send_mail(subject, message, *args, **kwargs)
        
        request = None
        if "request" in kwargs:
            request = kwargs.pop("request")
        
        return setting.mail_admins(
            subject=subject,
            message=message,
            html_message=kwargs.get("html_message"),
            fail_silently=kwargs.get("fail_silently", False),
            request_or_site=request,
        )