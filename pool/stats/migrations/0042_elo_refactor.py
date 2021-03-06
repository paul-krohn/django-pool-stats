# Generated by Django 2.1.11 on 2019-09-02 08:10

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stats', '0041_game_timestamp'),
    ]

    operations = [
        migrations.CreateModel(
            name='PlayerElo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.FloatField(blank=True, null=True)),
            ],
        ),
        migrations.RemoveField(
            model_name='game',
            name='away_elo',
        ),
        migrations.RemoveField(
            model_name='game',
            name='home_elo',
        ),
        migrations.AddField(
            model_name='playerelo',
            name='game',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='stats.Game'),
        ),
        migrations.AddField(
            model_name='playerelo',
            name='player',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='stats.Player'),
        ),
    ]
