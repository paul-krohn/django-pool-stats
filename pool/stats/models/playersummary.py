from datetime import date

from django.db import models
from trueskill import Rating

from .game import Game
from .player import Player
from .season import Season
from .scoresheet import ScoreSheet
from .team import Team
from .week import Week

from .globals import away_home, logger


class PlayerSeasonSummary(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    wins = models.IntegerField(verbose_name='Wins', default=0)
    losses = models.IntegerField(verbose_name='Losses', default=0)
    four_ohs = models.IntegerField(verbose_name='4-0s', default=0)
    table_runs = models.IntegerField(verbose_name='Table Runs', default=0)
    win_percentage = models.FloatField(verbose_name='Win Percentage', default=0.0, null=True)
    ranking = models.IntegerField(null=True)
    trueskill_mu = models.FloatField(null=True, blank=True)
    trueskill_sigma = models.FloatField(null=True, blank=True)

    def __str__(self):
        return "{} {}".format(self.player, self.season)

    class Meta:
        ordering = ['-win_percentage']

    def rating(self):
        return Rating(self.trueskill_mu, self.trueskill_sigma)

    def team(self):
        return self.player.team_set.filter(season=self.season).first()

    def update_sweeps(self):
        # the occasional player may have played for more than one
        # team in a season ...
        score_sheets = ScoreSheet.objects.filter(
            models.Q(match__away_team__in=self.player.team_set.filter(season=self.season))
            |
            models.Q(match__home_team__in=self.player.team_set.filter(season=self.season))
        ).filter(official=1)
        sweeps = 0

        for score_sheet in score_sheets:
            for ah in away_home:
                score_sheet_filter_args = {'{}_player'.format(ah): self.player}
                if len(score_sheet.games.filter(
                    **score_sheet_filter_args
                ).filter(
                    winner=ah
                )) == 4:
                    sweeps += 1
        self.four_ohs = sweeps
        self.save()

    @classmethod
    def update_rankings(cls, season_id, minimum_games=None):
        all_summaries = cls.objects.filter(season=season_id).order_by('-win_percentage', '-wins')
        # remove the players with < the minimum number of games in the current season
        summaries = []
        if minimum_games is None:
            minimum_games = len(Week.objects.filter(season_id=season_id, date__lt=date.today())) * \
                Season.objects.get(id=season_id).minimum_games
        for summary in all_summaries:
            if summary.wins + summary.losses >= minimum_games:
                summaries.append(summary)
            else:
                summary.ranking = 0
                summary.save()
        inc = 0
        while inc < len(summaries):
            tie_count = 0
            while inc + tie_count < len(summaries):
                # the first clause below is to prevent us trying to compare something off the end of the list
                if (inc+tie_count+1 < len(summaries)) and \
                                summaries[inc].win_percentage == summaries[inc+tie_count+1].win_percentage and \
                                summaries[inc].wins == summaries[inc + tie_count + 1].wins:
                    tie_count += 1
                else:
                    break
            for i in range(0, tie_count + 1):
                summaries[inc+i].ranking = inc + 1
                summaries[inc+i].save()
            inc += tie_count + 1

    def update(self):
        games = Game.objects.filter(
            scoresheet__match__season_id=self.season
        ).filter(
            scoresheet__official=True
        ).filter(
            scoresheet__match__playoff=False
        ).filter(
            forfeit=False
        )
        away_wins = games.filter(away_player=self.player).filter(winner='away')
        home_wins = games.filter(home_player=self.player).filter(winner='home')

        away_losses = games.filter(away_player=self.player).filter(winner='home')
        home_losses = games.filter(home_player=self.player).filter(winner='away')

        self.team = self.player.team_set.filter(season=self.season).first()

        logger.debug("{} has {} wins and {} losses".format(self, self.wins, self.losses))
        self.wins = len(away_wins) + len(home_wins)
        self.losses = len(away_losses) + len(home_losses)
        self.win_percentage = None
        if self.wins + self.losses > 0:
            self.win_percentage = self.wins / (self.wins + self.losses)

        self.table_runs = len(away_wins.filter(table_run=True)) + len(home_wins.filter(table_run=True))

        self.update_sweeps()

        self.save()

    @classmethod
    def update_all(cls, season_id, minimum_games=None):
        # find all the players on teams in this season
        teams = Team.objects.filter(season=season_id)
        for team in teams:
            for player in team.players.all():
                summaries = cls.objects.filter(season=season_id, player=player)
                if not len(summaries):
                    cls(season=Season.objects.get(id=season_id), player=player).save()

        for summary in cls.objects.filter(season=season_id):
            summary.update()
        cls.update_rankings(season_id, minimum_games)
