from datetime import date

from django.db import models


class Season(models.Model):
    name = models.CharField(max_length=200)
    pub_date = models.DateField('date of first week')
    registration_start = models.DateField(null=True)
    registration_end = models.DateField(null=True)
    is_default = models.BooleanField(default=False)
    minimum_games = models.IntegerField(null=True)

    def __str__(self):
        return self.name

    def standings_minimum_games(self, before_date=None):

        if before_date is None:
            before_date = date.today()

        min_games = 0
        for week in self.week_set.filter(date__lt=before_date):
            if len(week.match_set.filter(playoff=False)):
                min_games += self.minimum_games
        return min_games
