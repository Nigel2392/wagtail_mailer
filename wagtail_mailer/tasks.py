try:
    from celery import shared_task
except ImportError:
    
    class shared_task:
        def __init__(self, func=None, *args, **kwargs):
            self.func = func
        
        def __call__(self, *args, **kwargs):
            if self.func is None:
                # This is a decorator
                self.func = args[0]
                return self
            return self.func(*args, **kwargs)
        
        @property
        def __name__(self):
            return self.func.__name__
        
        @property
        def __doc__(self):
            return self.func.__doc__
        
        def __get__(self, instance, owner):
            return self.func.__get__(instance, owner)
        
        def delay(self, *args, **kwargs):
            return self.func(*args, **kwargs)
        
        @property
        def name(self):
            return self.func.__name__

from django.core.mail import (
    send_mass_mail as django_mass_mail,
    send_mail as django_send_mail,
)
from .mailing import (
    send_mass_mail,
    send_mail,
    send_mail_alternative,
    mail_admins,
)

@shared_task
def django_send_mass_mail_task(datatuple, fail_silently=True):
    """
        Send multiple emails to multiple recipients using Django's
        ``send_mass_mail`` function.

        Omits the ``auth_user``, ``auth_password`` and ``connection`` options
        This is because the ``get_connection`` function is not serializable, 
        and to keep celery from spilling secrets.
    
    """
    return django_mass_mail(
        datatuple=datatuple,
        fail_silently=fail_silently,
    )

@shared_task
def django_send_mail_task(
        subject,
        message,
        from_email,
        recipient_list,
        fail_silently=True,
        auth_user=None,
        auth_password=None,
        connection=None,
        html_message=None,
    ):
    """
        Send a single email to a recipient list using Django's
        ``send_mail`` function.

        Omits the ``auth_user``, ``auth_password`` and ``connection`` options
        This is because the ``get_connection`` function is not serializable,
        and to keep celery from spilling secrets.
    """

    return django_send_mail(
        subject=subject,
        message=message,
        from_email=from_email,
        recipient_list=recipient_list,
        fail_silently=fail_silently,
        auth_user=auth_user,
        auth_password=auth_password,
        connection=connection,
        html_message=html_message,
    )

@shared_task
def send_mass_mail_task(datatuple, mailbox_pk=None, mailbox=None, fail_silently=True, notify_admins=False):
    return send_mass_mail(
        datatuple=datatuple,
        mailbox_pk=mailbox_pk,
        mailbox=mailbox,
        fail_silently=fail_silently,
        notify_admins=notify_admins,
    )   
 
@shared_task
def send_mail_task(
        mailbox_pk,
        subject,
        message,
        recipient_list,
        html_message=None,
        fail_silently=True,
        notify_admins=False,
    ):

    return send_mail(
        mailbox_pk=mailbox_pk,
        subject=subject,
        message=message,
        recipient_list=recipient_list,
        html_message=html_message,
        fail_silently=fail_silently,
        notify_admins=notify_admins,
    )

@shared_task
def send_mail_alternative_task(
        subject="",
        body="",
        to=None,
        bcc=None,
        attachments=None,
        headers=None,
        alternatives=None,
        cc=None,
        reply_to=None,
        fail_silently=True,
        mailbox_pk=None,
    ):

    return send_mail_alternative(
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
        mailbox_pk=mailbox_pk,
    )


@shared_task
def mail_admins_task(
        mailbox_pk,
        subject,
        message,
        html_message=None,
        fail_silently=False,
    ):

    return mail_admins(
            subject=subject,
            message=message,
            mailbox_pk=mailbox_pk,
            html_message=html_message,
            fail_silently=fail_silently,
    )

