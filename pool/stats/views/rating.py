from django.shortcuts import get_object_or_404, render, redirect

from ..models import Player, PlayerRating


def rating(request, player_id):

    this_player = get_object_or_404(Player, id=player_id)
    ratings = PlayerRating.objects.filter(player=this_player).order_by(
        '-game__scoresheet__match__week__date',
        '-game__order'
    )

    context = {
        'player': this_player,
        'ratings': ratings,
    }

    rendered_page = render(request, 'stats/rating.html', context)
    return rendered_page


