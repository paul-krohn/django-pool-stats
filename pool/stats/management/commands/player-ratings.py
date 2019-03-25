#

"""
Implements trueskill.
"""
from django.core.management.base import BaseCommand

from trueskill import Rating, rate_1vs1

# from ....stats.models import Player, ScoreSheet, Team
from stats.models import Player, PlayerSeasonSummary, ScoreSheet, Team
# from ....stats.models.globals import away_home


class Command(BaseCommand):

    help = 'Calculates players\' trueskill ratings'

    sample_season_summary_id = 802

    def add_arguments(self, parser):
        parser.add_argument('season_id', nargs='+', type=int)

    def handle(self, *args, **options):
        for season_id in options['season_id']:

            # get all the games in the season. each game has the player IDs.
            # Season -> official score sheets -> games
            score_sheets = ScoreSheet.objects.filter(match__season_id=season_id, official=True)
            # print(score_sheets[0].games.all())
            ratings = dict()
            for score_sheet in score_sheets:
                for game in score_sheet.games.filter(forfeit=False):
                    # print(game)
                    # this is going to be so effing slow
                    home_player = PlayerSeasonSummary.objects.get(
                        player_id=game.home_player.id, season_id=season_id)
                    away_player = PlayerSeasonSummary.objects.get(
                        player_id=game.away_player.id, season_id=season_id)

                    if str(home_player.id) not in ratings:
                        ratings[str(home_player.id)] = Rating()
                    if str(away_player.id) not in ratings:
                        ratings[str(away_player.id)] = Rating()

                    winner = home_player
                    loser = away_player
                    if game.winner == 'away':
                        winner = away_player
                        loser = home_player

                    if home_player.id == self.sample_season_summary_id or \
                            away_player.id == self.sample_season_summary_id:
                        print("winner: %s loser: %s" % (winner, loser))

                    ratings[str(winner.id)], ratings[str(loser.id)] = \
                        rate_1vs1(ratings[str(winner.id)], ratings[str(loser.id)])

                    if winner.id == self.sample_season_summary_id or loser.id == self.sample_season_summary_id:
                        print(ratings[str(self.sample_season_summary_id)].mu)
