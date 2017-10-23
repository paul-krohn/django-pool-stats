# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-10-21 14:27
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stats', '0025_auto_20170819_0454'),
    ]

    operations = [
        migrations.CreateModel(
            name='Table',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
            ],
        ),
        migrations.AddField(
            model_name='match',
            name='table',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='stats.Table'),
        ),
        migrations.AddField(
            model_name='sponsor',
            name='tables',
            field=models.ManyToManyField(to='stats.Table'),
        ),
        migrations.AddField(
            model_name='team',
            name='table',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='stats.Table'),
        ),
    ]
