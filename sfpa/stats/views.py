from django.shortcuts import render
from .models import Season, Team


def set_season(request, season_id=None):
    if season_id is None:
        season_id = Season.objects.get(is_default=True).id
    request.session['season_id'] = season_id
    request.session.save()


def check_season(request):
    if 'season_id' in request.session:
        return
    else:
        set_season(request)


def index(request):
    check_season(request)
    team_list = Team.objects.filter(season=request.session['season_id'])
    context = {
        'teams': team_list
    }
    return render(request, 'stats/teams.html', context)


def team(request, team_id):

    _team = Team.objects.get(id=team_id)
    context = {
        'team': _team
    }
    return render(request, 'stats/team.html', context)


def seasons(request):
    _seasons = Season.objects.all()
    context = {
        'seasons': _seasons
    }
    return render(request, 'stats/seasons.html', context)
