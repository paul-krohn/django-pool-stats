# Generated by Django 3.2.5 on 2021-12-05 04:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('stats', '0047_add_trueskill'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='playerseasonsummary',
            name='rating',
        ),
    ]
