from django.shortcuts import render

from ..models import Match, PlayerSeasonSummary, ScoreSheet, Week
from ..models.player_rating import trueskill_env

from ..forms import MatchupForm

from trueskill import Rating

import itertools
import math


def win_probability(p1, p2):

    # cribbed from https://github.com/sublee/trueskill/issues/1
    team1 = [p1]
    team2 = [p2]
    delta_mu = sum(r.mu for r in team1) - sum(r.mu for r in team2)
    sum_sigma = sum(r.sigma ** 2 for r in itertools.chain(team1, team2))
    size = len(team1) + len(team2)
    denominator = math.sqrt(size * (trueskill_env.beta * trueskill_env.beta) + sum_sigma)
    return trueskill_env.cdf(delta_mu / denominator)


def get_player_matchups(kind, thing):
    matchups = []
    if kind == 'scoresheet':
        scoresheets = ScoreSheet.objects.filter(id=thing)
        if len(scoresheets) == 0:
            return matchups
        else:
            scoresheet = scoresheets[0]
        for game in scoresheet.games.all():
            if game.away_player and game.home_player:
                ap_summary = PlayerSeasonSummary.objects.get(season=scoresheet.match.season, player=game.away_player)
                hp_summary = PlayerSeasonSummary.objects.get(season=scoresheet.match.season, player=game.home_player)
                matchups.append({'away': ap_summary, 'home': hp_summary})
    elif kind == 'match':
        matches = Match.objects.filter(id=thing)
        if len(matches) == 0:
            return matchups
        else:
            match = matches[0]
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


def get_match(kind, thing):
    match = None
    if kind == 'match':
        matches = Match.objects.filter(id=thing)
        if len(matches):
            match = matches[0]
    elif kind == 'scoresheet':
        scoresheets = ScoreSheet.objects.filter(id=thing)
        if len(scoresheets):
            match = scoresheets[0].match
    return match


def matchup(request):

    kind = request.GET.get('kind', 'scoresheet')
    thing = request.GET.get('thing')
    week_id =  request.GET.get('week')
    assert kind in ['scoresheet', 'match']
    form = MatchupForm(request.GET)

    match_ups = []
    expected_wins = 0.0

    weeks = Week.objects.filter(season_id=request.session['season_id'])
    context = {
        'weeks': weeks,
        'form': form,
    }

    if kind and thing:
        for m in get_player_matchups(kind, int(thing)):
            if not(m['away'].rating and m['home'].rating):
                continue
            away_pct = win_probability(
                m['away'].rating,
                m['home'].rating,
            )
            expected_wins += away_pct
            match_ups.append({
                'away': m['away'], 'home': m['home'], 'pct': away_pct * 100
            })
        context.update({
            'match': get_match(kind, thing),
            'match_ups': match_ups,
            'expected_wins': 0 if not len(match_ups) else expected_wins / (len(match_ups) / 16.0)
        })

    if week_id:
        matches = Match.objects.filter(week_id=week_id)
        if kind == 'match':
            context.update({
                'matches': matches,
            })
        elif kind == 'scoresheet':
            score_sheets = ScoreSheet.objects.filter(match__week_id=week_id)
            context.update({
                'score_sheets': score_sheets,
            })
    return render(request, 'stats/matchup.html', context)
