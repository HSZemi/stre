# -*- coding: utf-8 -*-
# Generated by Django 1.9.8 on 2016-07-27 17:09
from __future__ import unicode_literals

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0004_antragsgrund_beschreibung'),
    ]

    operations = [
        migrations.AddField(
            model_name='semester',
            name='frist',
            field=models.DateField(default=datetime.datetime(2016, 7, 27, 17, 9, 52, 884687)),
            preserve_default=False,
        ),
    ]
