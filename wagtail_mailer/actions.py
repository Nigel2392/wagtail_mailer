from django.utils.translation import gettext_lazy as _
from wagtail.snippets.bulk_actions.snippet_bulk_action import SnippetBulkAction
from wagtail import hooks
from .models import AdminReceiver, Mailer


@hooks.register("register_bulk_action")
class TestMailBulkAction(SnippetBulkAction):
    display_name = _("Test Mail")
    aria_label = _("Send a test mail to server admins")
    action_type = "test_mail"
    template_name = "mailer/bulk_actions/test_mail.html"
    models = [
        Mailer,
    ]

    @classmethod
    def get_models(cls):
        return cls.models
    

    @classmethod
    def execute_action(cls, objects, **kwargs):
        number_of_objects = 0
        number_of_child_objects = 0

        base_queryset = AdminReceiver.objects.filter(receives_mail=True)

        receivers = base_queryset.values_list("email", flat=True).distinct()
        user_recv = base_queryset.values_list("user__email", flat=True).distinct()
        
        receivers = list(
            set(
                filter(None, list(receivers) + list(user_recv))
            )
        )

        if len(receivers) == 0:
            return number_of_objects, number_of_child_objects
        
        for obj in objects:
            obj: Mailer

            message = "This is a test mail from mailbox: %s <%d>" % (obj.email_host_user, obj.pk)
            obj.send_mail(
                subject="Test mail",
                message=message,
                recipient_list=list(receivers),
                html_message=f"<h1>{message}</h1>"
            )

            number_of_objects += 1
            number_of_child_objects += len(receivers)

        return number_of_objects, number_of_child_objects

    def get_success_message(self, num_parent_objects, num_child_objects):
        servers = num_parent_objects
        mails_sent = num_child_objects
        return _(
            f"{servers} Server(s) have sent messages to a total of {mails_sent} users. "
            "Please be patient, and check your spam folder."
        )
