# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-06-05 04:19
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stats', '0017_auto_20160605_0416'),
    ]

    operations = [
        migrations.AlterField(
            model_name='match',
            name='season',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='stats.Season'),
        ),
        migrations.AlterField(
            model_name='week',
            name='season',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='stats.Season'),
        ),
    ]
