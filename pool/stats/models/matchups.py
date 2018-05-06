from django.db import models

from .division import Division
from .week import Week


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
