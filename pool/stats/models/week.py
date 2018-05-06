from django.db import models

from .season import Season


class Week(models.Model):
    # a default season that doesn't bork migrations would be nice
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    date = models.DateField(null=True, blank=True)
    name = models.CharField(max_length=32, null=True)

    def __str__(self):
        return "{}".format(self.name)

    @classmethod
    def get_weeks_in_season(cls, before_after, week):
        comp_args = {
            'season_id': week.season,
            'date__{}'.format('lt' if before_after == 'before' else 'gt'): week.date
        }
        weeks = cls.objects.filter(**comp_args).order_by('date')
        if before_after == 'before':
            return list(weeks)[-1] if weeks else None
        else:
            return weeks[0] if weeks else None

    def next(self):
        return self.get_weeks_in_season(before_after='after', week=self)

    def previous(self):
        return self.get_weeks_in_season(before_after='before', week=self)

    def unused_teams(self):
        matches_this_week = self.match_set.all()
        used_teams = set([])
        for m in matches_this_week:
            used_teams.add(m.away_team.id)
            used_teams.add(m.home_team.id)
        return used_teams

    def used_teams(self, team_ids=[]):
        matches_this_week = self.match_set.all()
        used_teams = set([])
        for m in matches_this_week:
            if hasattr(m.away_team, 'id') and m.away_team.id not in team_ids:
                used_teams.add(m.away_team.id)
            if hasattr(m.home_team, 'id') and m.home_team.id not in team_ids:
                used_teams.add(m.home_team.id)
        return used_teams
