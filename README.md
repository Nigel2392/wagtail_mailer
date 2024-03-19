wagtail_mailer
==============

A Wagtail application to easily configure your email settings at runtime.

Celery support is included by default.  
All it has to be is installed and running; we will import `shared_task` from `celery`
and automatically use it to send emails asynchronously (unless specified otherwise).


Quick start
-----------

1. Add 'wagtail_mailer' to your INSTALLED_APPS setting like this:

   ```
   INSTALLED_APPS = [
   ...,
   'wagtail_mailer',
   ]
   ```

2. Configure logging for your application to use the exception email handler.
```python
   LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'wagtail_mailer': {
                'level': 'ERROR',
                "class": "wagtail_mailer.log.WagtailSettingsAdminEmailHandler",
                "filters": ["wagtail_settings_email_filter"],
                "include_html": True,
            },
        },
        'filters': {
            'wagtail_settings_email_filter': {
                '()': 'wagtail_mailer.log.WagtailSettingsEmailFilter',
            },
        },
        'loggers': {
            ...
            'django.request': {
                'handlers': ['wagtail_mailer'],
                'level': 'ERROR',
                'propagate': False,
            },
            ...
        },
   }
```

How to use?
-----------

Bind the `wagtail_mailer.models.Mailer` model to one of your models.  
Generally this would be some sort of settings model.

```python
from django.db import models
from wagtail_mailer.models import Mailer
from wagtail.contrib.settings.models import BaseGenericSetting, register_setting


@register_setting
class MySettings(BaseGenericSetting):
    mailer = models.ForeignKey(Mailer, on_delete=models.CASCADE, null=True, blank=True)
```

Now you can use the `wagtail_mailer.mailer.Mail` class to send emails.

```python
settings = MySettings.load()
settings.mailer.send_mail(
      subject='Hello',
      message='Hello World',
      recipient_list=[
         'john@example.com',
      ],
      notify_admins=True, # Send a copy to the admins
)
```

## Other methods

### Sending single emails
```python
    def send_mail(self, subject, message, recipient_list, html_message=None, notify_admins=False) -> int:
        """Sends a single email message to a recipient list."""
```

### Sending single emails without using the celery backend

```python
    def sync_send_mail(self, subject, message, recipient_list, html_message=None, notify_admins=False) -> int:
        """Sends a single email message to a recipient list without using the celery backend."""
```

### Including attachments in your email.

```python
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
        """Sends a single email message with alternative content (like an attachment) to a recipient list."""
```

### Sending emails using a template

```python
    def send_mail_template(self, subject, template_name, context, recipient_list, is_file=True, as_html=True, request=None, **mail_alternative_kwargs) -> int:
        """Send an email using a template."""
```

### Sending multiple emails

```python
    def send_mass_mail(self, datatuple, notify_admins=False):
        """
        Given a datatuple of (subject, message, from_email, recipient_list), send
        each message to each recipient list. Return the number of emails sent.
        """
```

### Sending multiple emails without using the celery backend

```python
    def sync_mass_mail(self, datatuple, notify_admins=False):
         """
         Given a datatuple of (subject, message, from_email, recipient_list), send
         each message to each recipient list without using the celery backend.
         Return the number of emails sent.
         """
```
