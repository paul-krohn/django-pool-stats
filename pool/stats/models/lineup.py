from django.db import models

from .player import Player
from .playposition import PlayPosition, AwayPlayPosition, HomePlayPosition


class GameOrder(models.Model):
    away_position = models.ForeignKey(
        AwayPlayPosition,
        related_name='away_position',
        on_delete=models.CASCADE,
    )
    home_position = models.ForeignKey(
        HomePlayPosition,
        related_name='home_position',
        on_delete=models.CASCADE,
    )
    home_breaks = models.BooleanField(default=True)
    order = models.IntegerField(null=True)
    tiebreaker = models.BooleanField(default=False)

    def __str__(self):
        return "{} ({} vs {})".format(self.order, self.away_position, self.home_position)

    def as_dict(self):
        return {
            'away_position': self.away_position.away_name,
            'home_position': self.home_position.home_name,
            'home_breaks': self.home_breaks,
            'order': self.order,
            'tiebreaker': self.tiebreaker,
        }

    class Meta:
        # the default/primary key sort is sometimes wrong
        ordering = ['order']


class LineupEntry(models.Model):
    player = models.ForeignKey(Player, null=True, blank=True, on_delete=models.CASCADE)
    position = models.ForeignKey(PlayPosition, null=True, on_delete=models.CASCADE)


class AwayLineupEntry(LineupEntry):
    class Meta:
        proxy = True


class HomeLineupEntry(LineupEntry):
    class Meta:
        proxy = True


class Substitution(models.Model):
    game_order = models.ForeignKey(GameOrder, on_delete=models.CASCADE)
    player = models.ForeignKey(Player, null=True, blank=True, on_delete=models.CASCADE)
    play_position = models.ForeignKey(PlayPosition, null=True, blank=True, on_delete=models.CASCADE)


class AwaySubstitution(Substitution):
    class Meta:
        proxy = True

    def __str__(self):
        return "{} enters as {} starting with game {}".format(
            self.player, self.play_position.away_name, self.game_order
        )


class HomeSubstitution(Substitution):
    class Meta:
        proxy = True

    def __str__(self):
        return "{} enters as {} starting with game {}".format(
            self.player, self.play_position.home_name, self.game_order
        )


