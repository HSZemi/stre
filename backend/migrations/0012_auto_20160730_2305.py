# -*- coding: utf-8 -*-
# Generated by Django 1.9.8 on 2016-07-30 21:05
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0011_auto_20160730_2302'),
    ]

    operations = [
        migrations.AlterField(
            model_name='brief',
            name='antrag',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='backend.Antrag'),
        ),
        migrations.AlterField(
            model_name='brief',
            name='datei',
            field=models.CharField(max_length=1024),
        ),
        migrations.AlterField(
            model_name='brief',
            name='vorlage',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='backend.Briefvorlage'),
        ),
    ]
