# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-02-21 20:30
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stats', '0003_sponsor'),
    ]

    operations = [
        migrations.AddField(
            model_name='team',
            name='sponsor',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='stats.Sponsor'),
        ),
    ]
