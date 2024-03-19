from wagtail import hooks
from django.contrib.auth.models import Permission

@hooks.register('register_permissions')
def register_permissions():
    return Permission.objects.filter(
        content_type__app_label='wagtail_mailer',
        codename__in=[
            'edit_server_password',
        ]
    )
