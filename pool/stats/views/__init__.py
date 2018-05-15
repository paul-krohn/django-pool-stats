import time
import datetime

from django.shortcuts import render, redirect, get_object_or_404
from ..models import Division, Match, ScoreSheet, Season, Sponsor, Team
from ..models import PlayerSeasonSummary

# from .score_sheet import *

import django.forms
import django.db.models

from django.core.cache import cache
from django.utils.cache import get_cache_key
from django.urls import reverse

import logging
logger = logging.getLogger(__name__)


def session_uid(request):
    if 'uid' not in request.session.keys():
        request.session['uid'] = str(hash(time.time()))[0:15]
    return request.session['uid']


def expire_page(request, path=None, query_string=None, method='GET'):
    """
    :param request: "real" request, or at least one providing the same scheme, host, and port as what you want to expire
    :param path: The path you want to expire, if not the path on the request
    :param query_string: The query string you want to expire, as opposed to the path on the request
    :param method: the HTTP method for the page, if not GET
    :return: None
    """
    if query_string is not None:
        request.META['QUERY_STRING'] = query_string
    if path is not None:
        request.path = path
    request.method = method

    # get_raw_uri and method show, as of this writing, everything used in the cache key
    # print('req uri: {} method: {}'.format(request.get_raw_uri(), request.method))
    key = get_cache_key(request)
    if key in cache:
        cache.delete(key)


def set_season(request, season_id=None):
    """
    Allow the user to set their season to a value other than the default.
    :param request:
    :param season_id: the season to use, if not the current default
    :return: bool
    """
    if season_id is None:
        season_id = Season.objects.get(is_default=True).id
    request.session['season_id'] = season_id
    request.session.save()
    # hard-coded urls are bad okay?
    return redirect(request.META.get('HTTP_REFERER', '/stats/'))


def is_stats_master(user):
    return user.groups.filter(name='statsmaster').exists()


def user_can_edit_scoresheet(request, score_sheet_id):

    s = ScoreSheet.objects.get(id=score_sheet_id)
    # you can edit a score sheet if it is not official and either you created it,
    # or you are an admin
    if (not s.official) and ((session_uid(request) == s.creator_session) or
                             request.user.is_superuser or is_stats_master(request.user)):
        return True
    else:
        return False


def check_season(request):
    if 'season_id' in request.session:
        return
    else:
        set_season(request)


def index(request):
    check_season(request)
    return redirect('teams', season_id=request.session['season_id'])


def teams(request, season_id=None):
    check_season(request)
    if season_id is None:
        return redirect('teams', season_id=request.session['season_id'])
    team_list = Team.objects.filter(season=season_id).order_by('-win_percentage')
    season = Season.objects.get(id=request.session['season_id'])
    context = {
        'teams': team_list,
        'season': season,
    }
    return render(request, 'stats/teams.html', context)


def team(request, team_id, after=None):

    check_season(request)

    _team = get_object_or_404(Team, id=team_id)
    _players = PlayerSeasonSummary.objects.filter(
        player_id__in=list([x.id for x in _team.players.all()]),
        season_id=_team.season.id,
    ).order_by('player__last_name')
    official_score_sheets = ScoreSheet.objects.filter(official=True).filter(
        django.db.models.Q(match__away_team=_team) | django.db.models.Q(match__home_team=_team)
    ).order_by('match__week__date')
    unofficial_score_sheets = ScoreSheet.objects.filter(official=False).filter(
        django.db.models.Q(match__away_team=_team) | django.db.models.Q(match__home_team=_team)
    ).order_by('match__week__date')

    # we don't expect people to actually use the 'after' parameter, it is really to make test data
    # with long-ago dates usable .
    if after is not None:
        after_parts = list(map(int, after.split('-')))
        after_date = datetime.date(after_parts[0], after_parts[1], after_parts[2])
    else:
        after_date = datetime.date.today()
    after_date -= datetime.timedelta(days=2)
    _matches = Match.objects.filter(week__date__gt=after_date).filter(
        django.db.models.Q(away_team=_team) | django.db.models.Q(home_team=_team)
    ).order_by('week__date')

    context = {
        'team': _team,
        'players': _players,
        'show_players': False,
        'official_score_sheets': official_score_sheets,
        'unofficial_score_sheets': unofficial_score_sheets,
        'matches': _matches,
    }
    return render(request, 'stats/team.html', context)


def seasons(request):
    _seasons = Season.objects.all()
    context = {
        'seasons': _seasons
    }
    return render(request, 'stats/seasons.html', context)


def sponsor(request, sponsor_id):
    _sponsor = get_object_or_404(Sponsor, id=sponsor_id)
    context = {
        'sponsor': _sponsor
    }
    return render(request, 'stats/sponsor.html', context)


def sponsors(request):
    _sponsors = Sponsor.objects.all()
    context = {
        'sponsors': _sponsors
    }
    return render(request, 'stats/sponsors.html', context)


def divisions(request, season_id=None):
    check_season(request)
    if season_id is None:
        return redirect('divisions', season_id=request.session['season_id'])
    _divisions = Division.objects.filter(season=request.session['season_id']).order_by('name')
    # this wrapper divisions dodge is needed so the teams within each division
    # can be sorted by ranking
    wrapper_divisions = []
    for _division in _divisions:
        _teams = Team.objects.filter(
            division=_division,
            season=request.session['season_id']
        ).order_by('ranking')
        wrapper_divisions.append({
            'division': _division,
            'teams': _teams
        })
    context = {
        'divisions': _divisions,
        'wrapper_divisions': wrapper_divisions

    }
    return render(request, 'stats/divisions.html', context)


def update_stats(request):
    # be sure about what season we are working on
    check_season(request)
    season_id = request.session['season_id']

    Team.update_teams_stats(season_id=season_id)
    # cache invalidation has to be called from a view, because we need access to a
    # request object to find the cache key.
    expire_args = {'season_id': season_id}
    expire_page(request, reverse('divisions', kwargs=expire_args))
    expire_page(request, reverse('teams', kwargs=expire_args))
    for a_team in Team.objects.filter(season_id=request.session['season_id']):
        expire_page(request, reverse('team', kwargs={'team_id': a_team.id}))

    PlayerSeasonSummary.update_all(season_id=season_id)
    for pss in PlayerSeasonSummary.objects.filter(season_id=season_id):
        expire_page(request, reverse('player', kwargs={'player_id': pss.player.id}))

    expire_page(request, reverse('players', kwargs={'season_id': season_id}))

    return redirect('teams')
