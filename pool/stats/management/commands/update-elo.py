import logging

from elo import Rating, rate_1vs1

from django.core.management.base import BaseCommand

from ...models import Game, PlayerSeasonSummary, ScoreSheet, Season
from ...models.globals import away_home

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
            if len(previous_season_summary):
                previous_elo = previous_season_summary[0].elo
                print("previous elo for {} ({}): {}".format(
                    previous_season_summary[0], previous_season_summary[0].player.id, previous_elo
                ))
    return Rating(previous_elo)


class Command(BaseCommand):
    help = 'Calculates players\' ELO rating'

    def add_arguments(self, parser):
        parser.add_argument('the_id', type=int)
        parser.add_argument('--type', type=str, default='season')

    @staticmethod
    def get_games_filter(options):
        main_filter_args = {
            'scoresheet__official': True,
            'scoresheet__match__playoff': False,
            'forfeit': False
        }
        if options['type'] == 'scoresheet':
            main_filter_args['scoresheet__id'] = options['the_id']
        elif options['type'] == 'season':
            main_filter_args['scoresheet__match__season_id'] = options['the_id']
        return main_filter_args

    @staticmethod
    def get_summaries(game, season_id):
        summaries = dict()
        for ah in away_home:
            player = getattr(game, '{}_player'.format(ah))
            try:
                summaries[ah] = PlayerSeasonSummary.objects.get(
                    season_id=season_id, player=player
                )
            except PlayerSeasonSummary.DoesNotExist as e:
                print(
                    "no season summary for {}({}) based on game id {}. error: {}".format(player, player.id, game.id, e))
        return summaries

    def update_elo_from_game(self, game, season_id):  # summaries, winner_index, loser_index):
        # if game.away_player is None or game.home_player is None:
        #     return False
        wl = ['winner', 'loser']
        summaries = self.get_summaries(game, season_id)
        winner = game.winner

        # if the winner is 'home'
        winner_index = away_home.index(winner)
        loser_index = 1 - away_home.index(winner)
        new_elos = {}
        # print(new_elos.get('winner'))
        # new_winner, new_loser = rate_1vs1(
        new_elos['winner'], new_elos['loser'] = rate_1vs1(
            Rating(get_old_elo(summaries[away_home[winner_index]])),
            Rating(get_old_elo(summaries[away_home[loser_index]])),
        )

        game.away_elo = new_elos[wl[winner_index]]
        game.home_elo = new_elos[wl[loser_index]]
        game.save()

        summaries[away_home[winner_index]].elo = new_elos['winner']
        summaries[away_home[loser_index]].elo = new_elos['loser']

        summaries[away_home[winner_index]].save()
        summaries[away_home[loser_index]].save()

        if self.verbosity >= 3:
            self.stdout.write("{} def {} new ratings: {:.1f}, {:.1f}".format(
                summaries[away_home[winner_index]].player,
                summaries[away_home[loser_index]].player,
                new_elos['winner'],
                new_elos['loser'])
            )

    def handle(self, *args, **options):

        # your linter may flag this as outside of init, but that's ok, `handle()` is as close as we'll get to `__init__()`.
        self.verbosity = options['verbosity']

        assert options['type'] in ['scoresheet', 'season']

        season_id = options['the_id']
        if options['type'] == 'scoresheet':
            season_id = ScoreSheet.objects.get(id=options['the_id']).match.season.id
        main_filter_args = self.get_games_filter(options)
        games = Game.objects.filter(
            **main_filter_args
        ).exclude(
            winner=''
        ).filter(
            away_elo=None
        ).filter(
            home_elo=None
        ).exclude(
            winner=None
        ).exclude(
            away_player=None
        ).exclude(
            home_player=None
        )
        for game in games:
            self.update_elo_from_game(game, season_id)

