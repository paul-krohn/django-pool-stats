# Generated by Django 2.0.3 on 2018-04-06 04:11

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stats', '0029_auto_20180318_1605'),
    ]

    operations = [
        migrations.AlterField(
            model_name='match',
            name='away_team',
            field=models.ForeignKey(blank=True, limit_choices_to=models.Q(season__is_default=True), null=True, on_delete=django.db.models.deletion.CASCADE, related_name='away_team', to='stats.AwayTeam'),
        ),
        migrations.AlterField(
            model_name='match',
            name='home_team',
            field=models.ForeignKey(blank=True, limit_choices_to=models.Q(season__is_default=True), null=True, on_delete=django.db.models.deletion.CASCADE, related_name='home_team', to='stats.HomeTeam'),
        ),
        migrations.AlterField(
            model_name='match',
            name='week',
            field=models.ForeignKey(limit_choices_to=models.Q(season__is_default=True), on_delete=django.db.models.deletion.CASCADE, to='stats.Week'),
        ),
        migrations.AlterField(
            model_name='scoresheet',
            name='official',
            field=models.IntegerField(choices=[(0, 'New'), (1, 'Official'), (2, 'Needs Changes')], default=0),
        ),
        migrations.AlterField(
            model_name='team',
            name='division',
            field=models.ForeignKey(limit_choices_to=models.Q(season__is_default=True), null=True, on_delete=django.db.models.deletion.CASCADE, to='stats.Division'),
        ),
    ]
