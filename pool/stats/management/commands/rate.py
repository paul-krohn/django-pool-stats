from django.core.management.base import BaseCommand

from ...models.player_rating import rate_games


class Command(BaseCommand):

    def handle(self, *args, **options):

        rate_games()
