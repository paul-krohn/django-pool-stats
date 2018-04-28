# Generated by Django 2.0.3 on 2018-04-21 03:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stats', '0031_weekdivisionmatchup'),
    ]

    operations = [
        migrations.AddField(
            model_name='team',
            name='division_ranking',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='scoresheet',
            name='match',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scoresheets', to='stats.Match'),
        ),
    ]
