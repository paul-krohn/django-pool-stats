from django.db import models
from django.utils import timezone

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
    away_elo = models.FloatField(null=True)
    home_elo = models.FloatField(null=True)
    winner = models.CharField(max_length=4, blank=True)
    order = models.ForeignKey(GameOrder, null=True, on_delete=models.CASCADE)
    table_run = models.BooleanField(default=False)
    forfeit = models.BooleanField(default=False)
    timestamp = models.DateTimeField(default=None, blank=True, null=True)

    __original_winner = None

    # this method of adding a timestamp cribbed from:
    # https://stackoverflow.com/questions/1355150/django-when-saving-how-can-you-check-if-a-field-has-changed
    def __init__(self, *args, **kwargs):
        super(Game, self).__init__(*args, **kwargs)
        self.__original_winner = self.winner

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):

        if self.__original_winner in [None, ''] and self.winner not in [None, '']:
            self.timestamp = timezone.now()

        super(Game, self).save(force_insert=force_insert, force_update=force_update)
        self.__original_winner = self.winner
