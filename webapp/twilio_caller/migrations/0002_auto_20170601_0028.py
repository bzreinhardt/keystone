# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-06-01 00:28
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('twilio_caller', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TwilioCall',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('caller_name', models.TextField()),
                ('caller_email', models.TextField()),
                ('caller_number', models.TextField()),
                ('recipient_name', models.TextField()),
                ('recipient_email', models.TextField()),
                ('recipient_number', models.TextField()),
                ('call_begin', models.DateTimeField()),
                ('call_end', models.DateTimeField()),
                ('twilio_sid', models.TextField()),
                ('twilio_recording_sid', models.TextField()),
                ('twilio_recording_url', models.TextField()),
            ],
        ),
        migrations.DeleteModel(
            name='Call',
        ),
    ]
