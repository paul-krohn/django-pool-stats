from django.db import models
from django.core.exceptions import ObjectDoesNotExist

from .division import Division
from .game import Game
from .lineup import GameOrder, LineupEntry, AwayLineupEntry, HomeLineupEntry
from .lineup import Substitution, AwaySubstitution, HomeSubstitution
from .player import Player, AwayPlayer, HomePlayer
from .playposition import PlayPosition, AwayPlayPosition, HomePlayPosition
from .season import Season
from .sponsor import Sponsor
from .toobig import ScoreSheet, Team, AwayTeam, HomeTeam, Match, Week

import logging
logger = logging.getLogger(__name__)

away_home = ['away', 'home']


def get_default_season():
    try:
        return Season.objects.get(is_default=True)
    except ObjectDoesNotExist:
        return None


class WeekDivisionMatchup(models.Model):

    week = models.ForeignKey(Week, on_delete=models.CASCADE, null=True)
    away_division = models.ForeignKey(
        Division,
        on_delete=models.CASCADE,
        limit_choices_to=models.Q(season__is_default=True),
        related_name='away_division',
    )
    home_division = models.ForeignKey(
        Division,
        on_delete=models.CASCADE,
        limit_choices_to=models.Q(season__is_default=True),
        related_name='home_division',
    )

    def __str__(self):
        return '{} @ {}'.format(self.away_division, self.home_division)
