import logging

from django.shortcuts import redirect

from .season import set_season, check_season

logger = logging.getLogger(__name__)


def index(request):
    check_season(request)
    return redirect('teams', season_id=request.session['season_id'])


