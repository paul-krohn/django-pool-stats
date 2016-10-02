from django import template
from django.conf import settings

register = template.Library()


@register.filter()
def row_even_odd(game_number):
    """Returns even or odd for the row for styling purposes"""
    game_number = int(game_number)
    if ((game_number - 1) % settings.LEAGUE['game_group_size'] + 1) % 2:
        return "odd"
    else:
        return "even"

