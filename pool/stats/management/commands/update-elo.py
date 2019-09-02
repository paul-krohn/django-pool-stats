import logging


from django.core.management.base import BaseCommand

from ...models import PlayerElo

logger = logging.getLogger('stats')
logger.debug("message")


class Command(BaseCommand):
    help = 'Calculates players\' ELO rating'

    def add_arguments(self, parser):
        parser.add_argument('the_id', type=int)
        parser.add_argument('--type', type=str, default='season')

    def handle(self, *args, **options):

        PlayerElo.update_season(options['the_id'])
        # your linter may flag this as outside of init, but that's ok, `handle()` is as close as we'll get to `__init__()`.
        # self.verbosity = options['verbosity']
        #
        # assert options['type'] in ['scoresheet', 'season']
        #
        # season_id = options['the_id']
        # if options['type'] == 'scoresheet':
        #     season_id = ScoreSheet.objects.get(id=options['the_id']).match.season.id
        # main_filter_args = self.get_games_filter(options)
        # games = Game.objects.filter(
        #     **main_filter_args
        # ).exclude(
        #     winner=''
        # ).filter(
        #     away_elo=None
        # ).filter(
        #     home_elo=None
        # ).exclude(
        #     winner=None
        # ).exclude(
        #     away_player=None
        # ).exclude(
        #     home_player=None
        # )
        # for game in games:
        #     self.update_elo_from_game(game, season_id)
        #
