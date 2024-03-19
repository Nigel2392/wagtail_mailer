import os
from django.db import models
from django.core.mail import EmailMessage, EmailMultiAlternatives, mail_admins
from django.core.files.uploadedfile import UploadedFile, InMemoryUploadedFile, TemporaryUploadedFile, SimpleUploadedFile
from django.core.files.storage import default_storage

import itertools
import logging

import json
import magic
from pathlib import Path

logger = logging.getLogger("wagtail_mailer")

def send_mass_mail(
            datatuple,
            mailbox=None,
            mailbox_pk=None,
            fail_silently=True,
            notify_admins=False,
        ):
    
    from .models import Mailer
    
    if mailbox is None and mailbox_pk is None:
        raise ValueError("Either mailbox or mailbox_pk must be provided")
    
    if mailbox is None:
        mailbox: Mailer = Mailer.objects.get(pk=mailbox_pk)

    if notify_admins:
        admins = mailbox.admin_receivers.all()
        count = admins.count()
        logger.info(f"Sending {len(datatuple)} mails from {mailbox.email_host_user} to {count} admins")
        if count == 0:
            logger.warning("No admin receivers for %s", mailbox)
        else:
            emails = [tup[3] for tup in datatuple]
            emails = set(itertools.chain.from_iterable(emails))

            admin_subject = f"Mailing logs for {mailbox}"
            email_list = "\n".join(emails)
            admin_message = f"Somebody sent a mail from {mailbox} to ({len(emails)} mailboxes): \n{email_list}"
            admin_recipients = admins \
                .annotate(
                    email_value = models.Case(
                        # if email is not empty, use it, otherwise use user email
                        models.When(
                            models.Q(email__isnull=False) & ~models.Q(email=""),
                            then=models.F("email"),
                        ),
                        default=models.F("user__email"),
                        output_field=models.CharField(max_length=255),
                    )
                )\
                .values_list("email_value", flat=True)
            
            admin_recipients = list(set(admin_recipients))

            datatuple = (
                (admin_subject, admin_message, mailbox.email_host_user, admin_recipients),
                *datatuple,
            )

    logger.info(f"Sending {len(datatuple)} mails from {mailbox.email_host_user}, (fail_silently={bool(fail_silently)}, notify_admins={bool(notify_admins)})")

    connection = mailbox.get_connection(fail_silently=fail_silently)

    messages = []
    for tup in datatuple:
        try:
            if len(tup) == 4:
                subject, message, sender, recipient = tup

                # make sure sender is not none, or falsy
                sender = sender or mailbox.email_host_user

                messages.append(EmailMessage(subject, message, sender, recipient, connection=connection))
            elif len(tup) == 5:
                subject, message, sender, recipient, html_message = tup

                # make sure sender is not none, or falsy
                sender = sender or mailbox.email_host_user

                email = EmailMultiAlternatives(subject, message, sender, recipient, connection=connection)
                email.attach_alternative(html_message, "text/html")
                messages.append(email)
            else:
                raise TypeError("Invalid number of values in tuple") 
        except Exception as e:
            logger.error(f"Error creating e-mail: {type(e)} {e}")
            if not fail_silently:
                raise e
    try:
        messages_sent = connection.send_messages(messages)
        if notify_admins:
            messages_sent -= 1
            
        mailbox.__class__.objects.filter(pk=mailbox.pk).update(emails_sent = models.F("emails_sent") + messages_sent)
        return messages_sent
    except Exception as e:
        logger.error(f"Error sending {len(datatuple)} e-mails: {type(e)} {e}")
        if not fail_silently:
            raise e
        return 0
    
class DescriptorGroup:
    def __init__(self, descriptors, zipname=None):
        self.descriptors: list[FileDescriptor] = descriptors
        self.zipname: str = zipname

    def __iter__(self):
        return iter(self.descriptors)
    
    def __len__(self):
        return len(self.descriptors)

    def __getitem__(self, index):
        return self.descriptors[index]

    def append(self, descriptor):
        self.descriptors.append(descriptor)

    def to_json(self) -> str:
        return json.dumps({
            'zipname': self.zipname,
            'descriptors': [d.to_json() for d in self],
        })

    @classmethod
    def from_json(cls, data: str, storage=None) -> "DescriptorGroup[FileDescriptor]":
        data = json.loads(data)
        descriptors = data['descriptors']
        descriptors = [FileDescriptor.from_json(d, storage=storage) for d in descriptors]
        return cls(
            descriptors=descriptors,
            zipname=data['zipname'],
        )
    
class FileDescriptor:
    def __init__(self, path: str, content_type: str, storage=None):
        self.path = path
        self.content_type = content_type
        self.storage = storage

    def __str__(self):
        return f"{self.path} ({self.content_type})"
    
    def __repr__(self):
        return f"FileDescriptor({self.path}, {self.content_type})"
    
    def _check_storage(self):
        if self.storage is None:
            raise ValueError("FileDescriptor: Storage is not set")
    
    def storage_open(self):
        self._check_storage()
        return self.storage.open(self.path)
    
    def storage_exists(self):
        self._check_storage()
        return self.storage.exists(self.path)
    
    def storage_delete(self):
        self._check_storage()
        return self.storage.delete(self.path)
    
    def storage_save(self, content, max_length=None):
        self._check_storage()
        return self.storage.save(self.path, content, max_length)
    
    def storage_path(self):
        self._check_storage()
        return self.storage.path(self.path)
    
    def storage_size(self):
        self._check_storage()
        return self.storage.size(self.path)

    def storage_url(self):
        self._check_storage()
        return self.storage.url(self.path)

    def to_json(self) -> str:
        return json.dumps({
            'path': self.path,
            'content_type': self.content_type,
        })
    
    @classmethod
    def from_files(cls, *files, zipname=None) -> "DescriptorGroup[FileDescriptor]":
        file_list = DescriptorGroup(
            descriptors=[],
            zipname=zipname,
        )
        for f in files:
            if isinstance(f, FileDescriptor):
                file_list.append(f)
                continue
            
            if isinstance(f, (UploadedFile, InMemoryUploadedFile, TemporaryUploadedFile, SimpleUploadedFile)):
                raise TypeError("FileDescriptor.from_files does not accept UploadedFile objects")
            
            path = f.path

            if hasattr(f, "content_type"):
                content_type = f.content_type
            else:
                content_type = magic.from_buffer(f.read(), mime=True)
                if hasattr(f, "seek"):
                    f.seek(0)
            file = cls(
                path=path,
                content_type=content_type
            )
            file_list.append(file)
        return file_list

    @classmethod
    def from_json(cls, data: str, storage=None) -> 'FileDescriptor':
        attributes = json.loads(data)
        return cls(
            path=attributes['path'],
            content_type=attributes['content_type'],
            storage=storage,
        )

from zipfile import ZipFile
from io import BytesIO

def send_mail_alternative(
    subject:                            str = "",
    body:                               str = "",
    to:                           list[str] = None,
    bcc:                          list[str] = None,
    attachments: list[dict[FileDescriptor]] = None,
    headers:                 dict[str, str] = None,
    alternatives:     list[tuple[str, str]] = None,
    cc:                           list[str] = None,
    reply_to:                     list[str] = None,
    fail_silently                           = True,
    mailbox                                 = None,
    mailbox_pk                              = None,
    notify_admins                           = False,
):
    
    from .models import Mailer
    
    if mailbox is None and mailbox_pk is None:
        raise ValueError("Either mailbox or mailbox_pk must be provided")
    
    if mailbox is None:
        mailbox: Mailer = Mailer.objects.get(pk=mailbox_pk)

    email = EmailMultiAlternatives(
        subject=subject,
        body=body,
        from_email=mailbox.email_host_user,
        to=to,
        bcc=bcc,
        headers=headers,
        alternatives=alternatives,
        cc=cc,
        reply_to=reply_to,
        connection=mailbox.get_connection(fail_silently=fail_silently)
    )

    if attachments:
        storage = default_storage

        descriptors = DescriptorGroup.from_json(attachments)
        
        logger.info(f"Sending email from {mailbox.email_host_user} to {to} with {len(descriptors)} attachments")

        zipFile = BytesIO()
        index = 0
        with ZipFile(zipFile, 'w') as zip:
            for descriptor in descriptors:
                file = storage.open(descriptor.path)
                filename = os.path.basename(descriptor.path)
                filename = f"{index}_{filename}"
                zip.writestr(filename, file.read())

                index += 1

        zipFile.seek(0)

        name = descriptors.zipname or "attachments.zip"

        email.attach(
            filename=name,
            content=zipFile.read(),
            mimetype="application/zip",
        )

        # for descriptor in descriptors:
        #     email.attach_file(
        #         path=storage.path(descriptor.path),
        #         mimetype=descriptor.content_type,
        #     )
    else:
        logger.info(f"Sending email from {mailbox.email_host_user} to {to} without attachments")

    return email.send()    
    

def send_mail(
        subject,
        message,
        recipient_list,
        mailbox_pk=None,
        mailbox=None,
        html_message=None,
        fail_silently=True,
        notify_admins=False,
    ):
    
    datatuple = [subject, message, None, recipient_list]
    if html_message:
        datatuple.append(html_message)
    datatuple = [datatuple]

    return send_mass_mail(
        mailbox=mailbox,
        mailbox_pk=mailbox_pk,
        datatuple=datatuple,
        fail_silently=fail_silently,
        notify_admins=notify_admins,
    )

def mail_admins(
        subject,
        message,
        mailbox_pk=None,
        mailbox=None,
        html_message=None,
        fail_silently=False,
    ):

    from .models import Mailer
    
    if mailbox is None and mailbox_pk is None:
        raise ValueError("Either mailbox or mailbox_pk must be provided")
    
    if mailbox is None:
        mailbox: Mailer = Mailer.objects.get(pk=mailbox_pk)

    connection = mailbox.get_connection(fail_silently=fail_silently)

    return mail_admins(
        subject=subject,
        message=message,
        connection=connection,
        html_message=html_message,
        fail_silently=fail_silently,
    )

