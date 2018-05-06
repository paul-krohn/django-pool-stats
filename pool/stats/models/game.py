from django.db import models

from .player import AwayPlayer, HomePlayer
from .lineup import GameOrder


class Game(models.Model):
    away_player = models.ForeignKey(
        AwayPlayer,
        null=True,
        blank=True,
        related_name='away_player',
        on_delete=models.CASCADE,
    )
    home_player = models.ForeignKey(
        HomePlayer,
        null=True,
        blank=True,
        related_name='home_player',
        on_delete=models.CASCADE,
    )
    winner = models.CharField(max_length=4, blank=True)
    order = models.ForeignKey(GameOrder, null=True, on_delete=models.CASCADE)
    table_run = models.BooleanField(default=False)
    forfeit = models.BooleanField(default=False)
