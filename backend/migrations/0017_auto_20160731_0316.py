# -*- coding: utf-8 -*-
# Generated by Django 1.9.8 on 2016-07-31 01:16
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0016_aktion_is_file_upload'),
    ]

    operations = [
        migrations.RenameField(
            model_name='aktion',
            old_name='is_file_upload',
            new_name='ist_upload',
        ),
    ]
