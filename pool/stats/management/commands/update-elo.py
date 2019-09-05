from django.core.management.base import BaseCommand

from ...models import PlayerElo


class Command(BaseCommand):
    help = 'Calculates players\' ELO rating'

    def add_arguments(self, parser):
        parser.add_argument('season_id', type=int)

    def handle(self, *args, **options):

        PlayerElo.update_season(options['season_id'])
