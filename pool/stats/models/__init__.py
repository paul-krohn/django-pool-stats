from django.core.exceptions import ObjectDoesNotExist

from .division import Division
from .game import Game
from .lineup import GameOrder, LineupEntry, AwayLineupEntry, HomeLineupEntry
from .lineup import Substitution, AwaySubstitution, HomeSubstitution
from .matchups import WeekDivisionMatchup
from .player import Player, AwayPlayer, HomePlayer
from .playposition import PlayPosition, AwayPlayPosition, HomePlayPosition
from .playersummary import PlayerSeasonSummary
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


