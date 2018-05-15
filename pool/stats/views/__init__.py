from django.shortcuts import redirect

from ..utils import expire_page
from .season import set_season, check_season
from ..models import Team
from ..models import PlayerSeasonSummary

from django.urls import reverse

import logging
logger = logging.getLogger(__name__)


def index(request):
    check_season(request)
    return redirect('teams', season_id=request.session['season_id'])


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
