# -*- coding: utf-8 -*-
# Generated by Django 1.9.8 on 2016-07-27 16:54
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='semester',
            old_name='semester',
            new_name='semestertyp',
        ),
        migrations.AddField(
            model_name='semester',
            name='jahr',
            field=models.CharField(default=2016, max_length=9),
            preserve_default=False,
        ),
    ]