# Generated by Django 2.0.3 on 2018-05-30 13:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stats', '0035_tie_tiebreakerresult'),
    ]

    operations = [
        migrations.AddField(
            model_name='tiebreakerresult',
            name='summary',
            field=models.TextField(default=None, max_length=1024),
        ),
    ]
