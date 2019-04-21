import logging

from elo import Rating, rate_1vs1

from django.core.management.base import BaseCommand
from django.db import models

from stats.models import Game, PlayerSeasonSummary, Season
from stats.models.globals import away_home

logger = logging.getLogger('stats')
logger.debug("message")


def get_previous_season(season_id):
    this_season = Season.objects.get(id=season_id)
    # now get the seasons before this one (ie excluding this one), ordered by date
    seasons = Season.objects.filter(pub_date__lt=this_season.pub_date).order_by('-pub_date')
    return seasons[0] or None


def get_old_elo(player_summary):

    # if the previous season is None, and there is no elo, return a new/default elo
    previous_elo = None
    if player_summary.elo is not None:
        previous_elo = player_summary.elo
    else:
        previous_season = get_previous_season(player_summary.season_id)
        if previous_season is not None:
            previous_season_summary = PlayerSeasonSummary.objects.filter(
                player=player_summary.player, season=previous_season
            )
            print(previous_season_summary)
            if len(previous_season_summary):
                previous_elo = previous_season_summary[0].elo
                print("previous elo for {} ({}): {}".format(
                    previous_season_summary[0], previous_season_summary[0].player.id, previous_elo
                ))
            # else:
            #     print('no summary for season {} player {}'.format(previous_season, player_summary.player))
    return Rating(previous_elo)


class Command(BaseCommand):
    help = 'Calculates players\' ELO rating'

    def add_arguments(self, parser):
        parser.add_argument('season_id', type=int)

    def handle(self, *args, **options):

        # your linter may flag this as outside of init, but that's ok, `handle()` is as close as we'll get to `__init__()`.
        self.verbosity = options['verbosity']

        season_id = options['season_id']

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
        count = 0
        for game in games:
            count += 1
            if game.away_player is None or game.home_player is None:
                continue
            summary = dict()
            for ah in away_home:
                player = getattr(game, '{}_player'.format(ah))
                try:
                    summary[ah] = PlayerSeasonSummary.objects.get(season_id=season_id, player=player)
                except PlayerSeasonSummary.DoesNotExist as e:
                    print("no season summary for {} based on game id {}. error: {}".format(player, game.id, e))

            winner = game.winner

            # if the winner is 'home'
            winner_index = away_home.index(winner)
            loser_index = 1 - away_home.index(winner)

            new_winner, new_loser = rate_1vs1(
                Rating(get_old_elo(summary[away_home[winner_index]])),
                Rating(get_old_elo(summary[away_home[loser_index]])),
            )

            summary[away_home[winner_index]].elo = new_winner
            summary[away_home[loser_index]].elo = new_loser

            summary[away_home[winner_index]].save()
            summary[away_home[loser_index]].save()

            if self.verbosity >= 3:
                self.stdout.write("{} def {} new ratings: {}, {}".format(
                    summary[away_home[winner_index]].player,
                    summary[away_home[loser_index]].player,
                    new_winner,
                    new_loser)
                )
