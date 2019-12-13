# Generated by Django 2.1.11 on 2019-12-11 18:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stats', '0042_elo_refactor'),
    ]

    operations = [
        migrations.CreateModel(
            name='Bracket',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.TextField(choices=[('w', 'Winners'), ('l', 'Losers')])),
            ],
        ),
        migrations.CreateModel(
            name='Participant',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.TextField(choices=[('team', 'Team'), ('player', 'Player'), ('doubles_players', 'Player')])),
                ('seed', models.IntegerField(blank=True, null=True)),
                ('place', models.IntegerField(blank=True, null=True)),
                ('doubles_players', models.ManyToManyField(blank=True, related_name='doubles_players', to='stats.Player')),
                ('player', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='stats.Player')),
                ('team', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='stats.Team')),
            ],
        ),
        migrations.CreateModel(
            name='Round',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.IntegerField(null=True)),
                ('bracket', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='stats.Bracket')),
            ],
        ),
        migrations.CreateModel(
            name='Tournament',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField()),
                ('creator_session', models.CharField(blank=True, max_length=16, null=True)),
                ('type', models.TextField(choices=[('singles', 'Singles'), ('scotch_doubles', 'Scotch Doubles'), ('teams', 'Teams')])),
                ('elimination', models.TextField(choices=[('single', 'Single Elimination'), ('double', 'Double Elimination')])),
                ('seeded', models.BooleanField(default=False)),
                ('flopped', models.BooleanField(default=False)),
                ('third_place', models.BooleanField(default=False)),
                ('show_places', models.IntegerField(default=1)),
                ('season', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='stats.Season')),
            ],
        ),
        migrations.CreateModel(
            name='TournamentMatchup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.IntegerField()),
                ('a_want_winner', models.NullBooleanField()),
                ('b_want_winner', models.NullBooleanField()),
                ('play_order', models.IntegerField(null=True)),
                ('is_necessary', models.BooleanField(default=True)),
                ('participant_a', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='participant_a', to='stats.Participant')),
                ('participant_b', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='participant_b', to='stats.Participant')),
                ('round', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='stats.Round')),
                ('source_match_a', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='match_a', to='stats.TournamentMatchup')),
                ('source_match_b', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='match_b', to='stats.TournamentMatchup')),
                ('winner', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='stats.Participant')),
            ],
        ),
        migrations.AddField(
            model_name='participant',
            name='tournament',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='stats.Tournament'),
        ),
        migrations.AddField(
            model_name='bracket',
            name='tournament',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='stats.Tournament'),
        ),
    ]
