from elo import Elo, Rating, expect
from django.core.management.base import BaseCommand
from django.db import models
from django.shortcuts import get_object_or_404, render, redirect

from stats.models import Game, Match, PlayerSeasonSummary, ScoreSheet, Season
from stats.models.globals import away_home


def get_player_matchups(kind, thing):
    matchups = []
    if kind == 'scoresheet':
        scoresheet = get_object_or_404(ScoreSheet, id=thing)
        for game in scoresheet.games.all():
            ap_summary = PlayerSeasonSummary.objects.get(season=scoresheet.match.season, player=game.away_player)
            hp_summary = PlayerSeasonSummary.objects.get(season=scoresheet.match.season, player=game.home_player)
            matchups.append({'away': ap_summary, 'home': hp_summary})
    elif kind == 'match':
        match = Match.objects.get(id=thing)
        for ap in match.away_team.players.all():
            for hp in match.home_team.players.all():
                matchups.append({
                    'away': PlayerSeasonSummary.objects.get(
                        season=match.season, player=ap
                    ),
                    'home': PlayerSeasonSummary.objects.get(
                        season=match.season, player=hp
                    )
                })
    return matchups

def matchup(request, ):
    e = Elo(beta=80)
    # kind = 'scoresheet', thing = None
    kind = request.GET.get('kind', 'scoresheet')
    thing = request.GET.get('thing')
    assert kind in ['scoresheet', 'match']

    match_ups = []
    expected_wins = 0.0

    if kind is None or thing is None:
        # default form here
        context = {}
    else:
        for m in get_player_matchups(kind, int(thing)):
            away_pct = e.expect(m['away'].elo, m['home'].elo)
            expected_wins += away_pct
            match_ups.append({
                'away': m['away'], 'home': m['home'], 'pct': away_pct
            })

        context = {
            'match_ups': match_ups,
            'expected_wins': expected_wins / (len(match_ups) / 16.0),
        }
    return render(request, 'stats/matchup.html', context)
