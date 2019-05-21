from django.db import models

from .season import Season
from .table import Table
from .week import Week


class Match(models.Model):
    # the `is_default` season being the default is set in the admin, rather than here,
    # doing it here breaks generating migrations with an empty database.
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    week = models.ForeignKey(Week, limit_choices_to=models.Q(season__is_default=True), on_delete=models.CASCADE)
    home_team = models.ForeignKey(
        'HomeTeam',
        limit_choices_to=models.Q(season__is_default=True),
        related_name='home_team',
        on_delete=models.CASCADE
    )
    away_team = models.ForeignKey(
        'AwayTeam',
        limit_choices_to=models.Q(season__is_default=True),
        related_name='away_team',
        on_delete=models.CASCADE
    )
    alternate_table = models.ForeignKey(Table, default=None, null=True, blank=True, on_delete=models.CASCADE)
    playoff = models.BooleanField(default=False)

    def __str__(self):
        return "{} @ {}".format(self.away_team, self.home_team)

    def table(self):
        return self.alternate_table if self.alternate_table else self.home_team.table

    class Meta:
        verbose_name = 'Match'
        verbose_name_plural = 'Matches'


