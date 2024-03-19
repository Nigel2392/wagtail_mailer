# Generated by Django 5.0.1 on 2024-03-19 12:26

import django.db.models.deletion
import modelcluster.fields
import wagtail.blocks
import wagtail.fields
import wagtail_mailer.models.mailer
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ExceptionMailSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status_code_ranges', wagtail.fields.StreamField([('status_code_range', wagtail.blocks.StructBlock([('start', wagtail.blocks.IntegerBlock(default=400, help_text='The start of the status code range.', max_value=599, min_value=100, required=True)), ('end', wagtail.blocks.IntegerBlock(default=599, help_text='The end of the status code range.', max_value=599, min_value=100, required=True))]))], blank=True, null=True, use_json_field=True)),
            ],
            options={
                'verbose_name': 'Exception Mail Settings',
                'verbose_name_plural': 'Exception Mail Settings',
            },
        ),
        migrations.CreateModel(
            name='Mailer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('emails_sent', models.IntegerField(default=0, editable=False, help_text='The number of emails sent')),
                ('email_host', models.CharField(help_text='The email host', max_length=255)),
                ('email_port', models.IntegerField(default=587, help_text='The email port')),
                ('email_host_user', models.EmailField(help_text='The email host user', max_length=255, null=True)),
                ('email_host_password', wagtail_mailer.models.mailer.PasswordField(help_text='The email host password', max_length=255, null=True)),
                ('email_use', models.CharField(choices=[('1', 'TLS'), ('2', 'SSL'), ('3', 'NONE')], default='3', help_text='The email use', max_length=255)),
                ('email_timeout', models.IntegerField(default=60, help_text='The email timeout in seconds')),
                ('email_fail_silently', models.BooleanField(default=False, help_text='Fail silently')),
            ],
            options={
                'verbose_name': 'Mail Server',
                'verbose_name_plural': 'Mail Servers',
                'permissions': [('edit_server_password', 'Can edit server password')],
            },
        ),
        migrations.CreateModel(
            name='ExceptionReceiver',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sort_order', models.IntegerField(blank=True, editable=False, null=True)),
                ('email', models.EmailField(help_text='The email address to send emails to', max_length=255)),
                ('description', models.CharField(blank=True, help_text='A description of the user, or their occupation within the company.', max_length=255, null=True)),
                ('settings', modelcluster.fields.ParentalKey(on_delete=django.db.models.deletion.CASCADE, related_name='exception_receivers', to='wagtail_mailer.exceptionmailsettings')),
            ],
            options={
                'verbose_name': 'Exception Receiver',
                'verbose_name_plural': 'Exception Receivers',
            },
        ),
        migrations.AddField(
            model_name='exceptionmailsettings',
            name='mailbox',
            field=models.ForeignKey(help_text='The mailbox to send exception emails from', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='exception_mail_settings', to='wagtail_mailer.mailer', verbose_name='Mailbox'),
        ),
        migrations.CreateModel(
            name='AdminReceiver',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sort_order', models.IntegerField(blank=True, editable=False, null=True)),
                ('receives_mail', models.BooleanField(default=True, help_text='Whether or not the email address receives emails')),
                ('email', models.EmailField(blank=True, help_text='The email address to send emails to', max_length=255, null=True, unique=True)),
                ('first_name', models.CharField(blank=True, help_text='The first name of the email recipient', max_length=255, null=True)),
                ('last_name', models.CharField(blank=True, help_text='The last name of the email recipient', max_length=255, null=True)),
                ('user', models.ForeignKey(blank=True, help_text='The user associated with the email address', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='User')),
                ('mailbox', modelcluster.fields.ParentalKey(on_delete=django.db.models.deletion.CASCADE, related_name='admin_receivers', to='wagtail_mailer.mailer', verbose_name='Mailbox')),
            ],
            options={
                'verbose_name': 'Admin Receiver',
                'verbose_name_plural': 'Admin Receivers',
            },
        ),
        migrations.CreateModel(
            name='Receiver',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('receives_mail', models.BooleanField(default=True, help_text='Whether or not the email address receives emails')),
                ('email', models.EmailField(blank=True, help_text='The email address to send emails to', max_length=255, null=True, unique=True)),
                ('first_name', models.CharField(blank=True, help_text='The first name of the email recipient', max_length=255, null=True)),
                ('last_name', models.CharField(blank=True, help_text='The last name of the email recipient', max_length=255, null=True)),
                ('user', models.ForeignKey(blank=True, help_text='The user associated with the email address', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'Receiver',
                'verbose_name_plural': 'Receivers',
            },
        ),
    ]
