from django.shortcuts import render

from django.http import HttpResponse
from .models import Season, Team


def index(request):
    team_list = Team.objects.all()
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
    seasons = Season.objects.all()
    context = {
        'seasons': seasons
    }
    return render(request, 'stats/seasons.html', context)


