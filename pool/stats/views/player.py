import datetime

from django.db import models
from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse

from ..forms import PlayerForm
from ..models import Player, PlayerSeasonSummary, ScoreSheet, Season
from ..views import logger
from ..views import check_season


def get_player_season_score_sheets(a_player, season):

    score_sheets_with_dupes = ScoreSheet.objects.filter(official=True).filter(
        models.Q(away_lineup__player=a_player) |
        models.Q(home_lineup__player=a_player) |
        models.Q(away_substitutions__player=a_player) |
        models.Q(home_substitutions__player=a_player)
    ).order_by('match__week__date').filter(match__week__season=season)
    # there are dupes in _score_sheets at this point, so we have to remove them; method is cribbed from:
    # http://stackoverflow.com/questions/480214/how-do-you-remove-duplicates-from-a-list-in-python-whilst-preserving-order
    seen = set()
    seen_add = seen.add
    return [x for x in score_sheets_with_dupes if not (x in seen or seen_add(x))]


def player_elo_history(request, player_id, season_id, limit=None):
    a_player = Player.objects.get(id=player_id)
    a_season = Season.objects.get(id=season_id)
    score_sheets = get_player_season_score_sheets(a_player, a_season)
    elo_history = []
    for ss in score_sheets:
        new_elo=None
        for game in ss.games.filter(
                forfeit=False
            ).exclude(
                away_player=None
            ).exclude(
                home_player=None
            ).filter(models.Q(away_player=a_player) | models.Q(home_player=a_player)):
            if a_player == game.away_player:
                new_elo = game.away_elo
            else:
                new_elo = game.home_elo
        if new_elo:
            elo_history.append({'t': ss.match.week.date, 'y': round(new_elo)    })

    return JsonResponse(elo_history[None if not limit else -limit:None], safe=False)


def player(request, player_id, season_id=None):
    check_season(request)
    detail_season = Season.objects.get(id=season_id or request.session['season_id'])
    _player = get_object_or_404(Player, id=player_id)
    summaries = PlayerSeasonSummary.objects.filter(player__exact=_player).order_by('-season')

    season_score_sheets = get_player_season_score_sheets(_player, detail_season)
    score_sheet_summaries = []
    # now scrape through the score sheets; collect games from each scoresheet, with win true/falsed and TRs marked
    for _score_sheet in season_score_sheets:
        this_score_sheet = {
            'id': _score_sheet.id,
            'match': _score_sheet.match,
            'games': []
        }
        for game in _score_sheet.games.all():
            if not game.winner or game.forfeit or game.away_player is None or game.home_player is None:
                continue  # skip not-won games, ie forfeits and unplayed playoff games
            if _player not in [game.away_player, game.home_player]:
                continue  # skip games not involving this player
            this_game = {
                'table_run': game.table_run,
                'opponent': game.home_player,
                'win': game.winner == 'away',
            }
            if _player == game.home_player:
                this_game['opponent'] = game.away_player
                this_game['win'] = game.winner == 'home'
            this_score_sheet['games'].append(this_game)
        score_sheet_summaries.append(this_score_sheet)
    context = {
        'detail_season': detail_season,
        'elo': request.GET.get('elo', False),
        'score_sheet_summaries': score_sheet_summaries,
        'summaries': summaries,
        'player': _player,
    }
    rendered_page = render(request, 'stats/player.html', context)
    return rendered_page


def players(request, season_id=None):
    check_season(request)

    if season_id is None:
        return redirect('players', season_id=request.session['season_id'])

    _players = PlayerSeasonSummary.objects.filter(
        season=season_id,
        ranking__gt=0
    ).order_by('-win_percentage', '-wins')
    show_teams = True

    context = {
        'elo': request.GET.get('elo', False),
        'players': _players,
        'show_teams': show_teams,  # referenced in the player_table.html template
        'season_id': request.session['season_id'],
    }
    view = render(request, 'stats/players.html', context)
    return view


def player_create(request):
    if request.method == 'POST':
        player_form = PlayerForm(request.POST)
        if player_form.is_valid():
            p = Player()
            logger.debug(player_form.cleaned_data['team'])
            t = player_form.cleaned_data['team']
            if player_form.cleaned_data['display_name'] is not '':
                p.display_name = player_form.cleaned_data['display_name']
            p.first_name = player_form.cleaned_data['first_name']
            p.last_name = player_form.cleaned_data['last_name']
            p.save()
            t.players.add(p)
            return redirect('team', t.id)
    else:
        player_form = PlayerForm()
    context = {
        'form': player_form
    }
    return render(request, 'stats/player_create.html', context)