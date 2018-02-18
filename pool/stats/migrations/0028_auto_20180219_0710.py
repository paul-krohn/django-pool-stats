# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-02-19 07:10
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stats', '0027_remove_playerseasonsummary_team'),
    ]

    operations = [
        migrations.AlterField(
            model_name='match',
            name='away_team',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='away_team', to='stats.AwayTeam'),
        ),
        migrations.AlterField(
            model_name='match',
            name='home_team',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='home_team', to='stats.HomeTeam'),
        ),
        migrations.AlterField(
            model_name='match',
            name='season',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='stats.Season'),
        ),
    ]
