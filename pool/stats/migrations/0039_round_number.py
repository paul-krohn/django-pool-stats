# Generated by Django 2.0.3 on 2018-07-04 15:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stats', '0038_auto_20180702_0511'),
    ]

    operations = [
        migrations.AddField(
            model_name='round',
            name='number',
            field=models.IntegerField(null=True),
        ),
    ]
