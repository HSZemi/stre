# -*- coding: utf-8 -*-
# Generated by Django 1.9.8 on 2016-07-31 17:26
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0019_remove_person_geburtsort'),
    ]

    operations = [
        migrations.AddField(
            model_name='aktion',
            name='sort',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='antragsgrund',
            name='sort',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='briefvorlage',
            name='sort',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='nachweis',
            name='sort',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
    ]
