from django.shortcuts import get_object_or_404, render, redirect

from ..models import Player, PlayerRating
from ..utils import page_cache as cache


def rating(request, player_id):

    player_rating_cache_key = '.'.join(['rating', str(player_id)])
    player_ratings = cache.get(player_rating_cache_key)

    if not player_ratings:

        this_player = get_object_or_404(Player, id=player_id)
        ratings = PlayerRating.objects.filter(player=this_player).order_by(
            '-game__scoresheet__match__week__date',
            '-game__order'
        )

        context = {
            'player': this_player,
            'ratings': ratings,
        }

        player_ratings = render(request, 'stats/rating.html', context)
        cache.set(player_rating_cache_key, player_ratings)
    return player_ratings
