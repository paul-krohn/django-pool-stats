# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-08-26 04:51
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stats', '0029_tournamentmatch_winner'),
    ]

    operations = [
        migrations.AddField(
            model_name='tournamentmatch',
            name='player_a_match',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='player_a_match', to='stats.Player'),
        ),
        migrations.AddField(
            model_name='tournamentmatch',
            name='player_b_match',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='player_b_match', to='stats.Player'),
        ),
    ]
