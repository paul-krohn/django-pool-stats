# Generated by Django 2.1.11 on 2019-08-29 05:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stats', '0040_match_no_null_teams'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='timestamp',
            field=models.DateTimeField(blank=True, default=None, null=True),
        ),
    ]