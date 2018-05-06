from django.db import models

from .season import Season
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
        blank=True, null=True,
        on_delete=models.CASCADE
    )
    away_team = models.ForeignKey(
        'AwayTeam',
        limit_choices_to=models.Q(season__is_default=True),
        related_name='away_team',
        blank=True, null=True,
        on_delete=models.CASCADE
    )
    playoff = models.BooleanField(default=False)

    def __str__(self):
        # return "{} @ {} ({} {})".format(self.away_team, self.home_team, self.season, self.week)
        return "{} @ {}".format(self.away_team, self.home_team)

    class Meta:
        verbose_name = 'Match'
        verbose_name_plural = 'Matches'


