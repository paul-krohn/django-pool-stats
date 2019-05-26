import logging

from django.core.management.base import BaseCommand
from ...models import Team, ScoreSheet
from ...models.globals import away_home

from django.db import models


logger = logging.getLogger('main')
logger.info("message")


class Command(BaseCommand):
    help = 'Calculates players\' (dis)advantage when breaking'

    def add_arguments(self, parser):
        parser.add_argument('team_id', nargs='+', type=int)

    def handle(self, *args, **options):
        for team_id in options['team_id']:
            records = dict()
            overall_record = [[0, 0], [0, 0]]
            for _player in Team.objects.get(id=team_id).players.all():
                _score_sheets_with_dupes = ScoreSheet.objects.filter(official=True).filter(
                        models.Q(away_lineup__player=_player) |
                        models.Q(home_lineup__player=_player) |
                        models.Q(away_substitutions__player=_player) |
                        models.Q(home_substitutions__player=_player)
                    ).order_by('match__week__date')
                seen = set()
                seen_add = seen.add
                _score_sheets = [x for x in _score_sheets_with_dupes if not (x in seen or seen_add(x))]
                record = [
                    # break w, l
                    [0, 0],
                    # no break w, l
                    [0, 0]
                ]
                for s in _score_sheets:
                    # the games involving _player, where they broke
                    home_match = _player in s.match.home_team.players.all()
                    for ah in away_home:
                        home_break = int(ah=='home')
                        args = {
                            '{}_player'.format(away_home[int(home_match)]): _player,
                            'order__home_breaks': home_break,
                            'forfeit': False,
                        }
                        games = s.games.filter(**args)
                        win_games = len(games.filter(winner=away_home[int(home_match)]))
                        loss_games = len(games.filter(winner=away_home[1 - int(home_match)]))
                        record[1 - home_break][0] += win_games
                        record[1 - home_break][1] += loss_games
                        overall_record[1 - home_break][0] += win_games
                        overall_record[1 - home_break][1] += loss_games
                records.update({str(_player): record})
            records.update({'overall': overall_record})
            print(Team.objects.get(id=team_id))
            print('{0:>28} {1:>11}'.format('break', 'nobreak'))
            print('{0:>16} {1:>5} {2:>5} {3:>5} {4:>5} {5:>6} '.format('player', 'w', 'l', 'w', 'l', 'adv'))
            for player_record in records:
                adv = 0.0
                if (records[player_record][0][0] + records[player_record][0][1]) > 0 and \
                        records[player_record][1][0] + records[player_record][1][1] >0:
                    adv = records[player_record][0][0] / (records[player_record][0][0] + records[player_record][0][1]) - records[player_record][1][0] / (records[player_record][1][0] + records[player_record][1][1])

                print('{name:>16} {bw:5} {bl:5} {nw:5} {nl:5} {yarr: .3f}'.format(
                    name=player_record, bw=records[player_record][0][0], bl=records[player_record][0][1],
                    nw=records[player_record][1][0], nl=records[player_record][1][1], yarr=adv)
                )
            print()
