from django import template
from django.conf import settings

register = template.Library()


@register.filter()
def row_even_odd(game_order):
    """Returns even or odd for the row for styling purposes"""
    if game_order.tiebreaker:
        return 'even'
    try:
        game_number = int(game_order.name)
    except ValueError:
        game_number = 2
    if ((game_number - 1) % settings.LEAGUE['game_group_size'] + 1) % 2:
        return 'odd'
    else:
        return 'even'


@register.filter()
def row_divider(game_order):
    if not game_order.tiebreaker and (int(game_order.name) % settings.LEAGUE['game_group_size'] == 0):
        return True
    return False
