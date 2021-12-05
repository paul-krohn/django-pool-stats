from django.db import models
from django.shortcuts import get_object_or_404, render, redirect
from django.template import loader

from ..models import Player, PlayerSeasonSummary, PlayerRating, Season
from ..utils import page_cache as cache
from ..views import logger
from ..views.season import CheckSeason


def rating(request, player_id):

    this_player = get_object_or_404(Player, id=player_id)
    ratings = PlayerRating.objects.filter(player=this_player).order_by('-game__scoresheet__match__week__date')

    context = {
        'player': this_player,
        'ratings': ratings,
    }

    rendered_page = render(request, 'stats/rating.html', context)
    return rendered_page


