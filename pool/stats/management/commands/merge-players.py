from django.core.management.base import BaseCommand

from ...models import Player, Game
from ...models.globals import away_home


def player_string(player):
    return '/'.join([str(player), str(player.id)])


class Command(BaseCommand):
    help = 'Merge games and team memberships from source_plater to destination_player. Optionally delete source_player.'


    def add_arguments(self, parser):
        parser.add_argument('source_player', type=int)
        parser.add_argument('destination_player', type=int)
        parser.add_argument('--delete', default=False, action='store_true')

    def update_teams(self, source_player, destination_player):

        altered_seasons = []

        teams = source_player.team_set.all()

        self.stdout.write("{} teams to update".format(len(teams)))

        for team in teams:
            team.players.remove(source_player)
            team.players.add(destination_player)
            team.save()
            season = team.season
            if season not in altered_seasons:
                altered_seasons.append(season)

            self.stdout.write("for team {}, removed {} and added {}".format(
                team,
                player_string(source_player),
                player_string(destination_player),
            ))
        return altered_seasons

    def update_games(self, source_player, destination_player):
        altered_seasons = []
        for ah in away_home:
            self.stdout.write("move {} games from {} to {}".format(
                ah,
                player_string(source_player),
                player_string(destination_player),
            ))
            ah_player_string = '{}_player'.format(ah)
            games_filter_args = {
                ah_player_string: source_player
            }
            games = Game.objects.filter(**games_filter_args)
            self.stdout.write("{} games to update".format(len(games)))
            for game in games:
                setattr(game, ah_player_string, destination_player)
                setattr(game, '{}_elo'.format(ah_player_string), None)
                game.save()
                try:
                    season =  game.scoresheet_set.all()[0].match.season
                    if season not in altered_seasons:
                        altered_seasons.append(season)
                except IndexError:
                    pass
        return altered_seasons

    def handle(self, *args, **options):

        altered_seasons = []

        source_player = Player.objects.get(id=options['source_player'])
        destination_player = Player.objects.get(id=options['destination_player'])

        self.stdout.write("source player: {}".format(player_string(source_player)))
        self.stdout.write("destination player: {}".format(player_string(destination_player)))

        altered_seasons += self.update_teams(source_player, destination_player)
        altered_seasons += self.update_games(source_player, destination_player)

        if options['delete']:
            source_player.delete()

        self.stdout.write("seasons altered: {}".format(str(altered_seasons)))
