from elo import Rating, rate_1vs1

from django.core.management.base import BaseCommand
from django.db import models

from stats.models import Game, PlayerSeasonSummary
from stats.models.globals import away_home


class Command(BaseCommand):
    help = 'Calculates players\' ELO rating'

    def add_arguments(self, parser):
        parser.add_argument('season_id', nargs='+', type=int)

    def handle(self, *args, **options):
        for season_id in options['season_id']:
            # records = dict()
            # overall_record = [[0, 0], [0, 0]]

            games = Game.objects.filter(
                scoresheet__match__season_id=season_id
            ).filter(
                scoresheet__official=True
            ).filter(
                scoresheet__match__playoff=False
            ).filter(
                forfeit=False
            ).exclude(
                winner=''
            )

            for game in games:
                summary = dict()
                for ah in away_home:
                    player = getattr(game, '{}_player'.format(ah))
                    summary[ah] = PlayerSeasonSummary.objects.get(season_id=season_id, player=player)
                print("working on game between {} and {} in game {}".format(
                    summary['away'].player, summary['home'].player, game.id)
                )
                winner = game.winner

                # if the winner is 'home'
                winner_index = away_home.index(winner)
                loser_index = 1 - away_home.index(winner)

                new_winner, new_loser = rate_1vs1(
                    Rating(summary[away_home[winner_index]].elo),
                    Rating(summary[away_home[loser_index]].elo)
                )

                summary[away_home[winner_index]].elo = new_winner
                summary[away_home[loser_index]].elo = new_loser

                summary[away_home[winner_index]].save()
                summary[away_home[loser_index]].save()

                print("{} def {} new ratings: {}, {}".format(
                    summary[away_home[winner_index]].player,
                    summary[away_home[loser_index]].player,
                    new_winner,
                    new_loser)
                )
