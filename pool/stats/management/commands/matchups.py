from elo import Elo, Rating, expect
from django.core.management.base import BaseCommand
from django.db import models

from stats.models import Game, Match, PlayerSeasonSummary, ScoreSheet, Season
from stats.models.globals import away_home


def get_previous_season(season_id):
    this_season = Season.objects.get(id=season_id)
    # now get the seasons before this one (ie excluding this one), ordered by date
    seasons = Season.objects.filter(pub_date__lt=this_season.pub_date).order_by('-pub_date')
    return seasons[0] or None


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('match_id', type=int)
        parser.add_argument('-s', dest='scoresheet', type=bool, default=False)

    def handle(self, *args, **options):
        e = Elo(beta=29)
        scoresheet = ScoreSheet.objects.get(id=options['match_id'])

        match = scoresheet.match
        players = dict()
        for ah in away_home:
            team = getattr(match, '{}_team'.format(ah))
            print('{} team: {}'.format(ah, team))
            players[ah] = team.players.all()

        away_win_cumul = 0.0

        for game in scoresheet.games.all():
            ap_summary = PlayerSeasonSummary.objects.get(season=scoresheet.match.season,player=game.away_player)
            hp_summary = PlayerSeasonSummary.objects.get(season=scoresheet.match.season,player=game.home_player)
            away_win_p = e.expect(ap_summary.elo, hp_summary.elo)
            away_win_cumul += away_win_p
            print("{ap} vs {hp}: {p:.1f}%".format(
                ap=ap_summary.player, hp=hp_summary.player, p=away_win_p * 100))

        print("expected wins for {}: {:.2f}".format(match.away_team, away_win_cumul))

    # def handle(self, *args, **options):
    #     for match_id in options['match_id']:
    #         match = Match.objects.get(id=match_id)
    #         players = dict()
    #         for ah in away_home:
    #             team = getattr(match, '{}_team'.format(ah))
    #             print('{} team: {}'.format(ah, team))
    #             players[ah] = team.players.all()
    #
    #         away_win_cumul = 0.0
    #
    #         for ap in players[away_home[0]]:
    #             ap_summary = PlayerSeasonSummary.objects.get(season=match.season, player=ap)
    #             for hp in players[away_home[1]]:
    #                 hp_summary = PlayerSeasonSummary.objects.get(season=match.season, player=hp)
    #
    #                 away_win_p = expect(ap_summary.elo, hp_summary.elo)
    #                 away_win_cumul += away_win_p
    #                 print("{ap} vs {hp}: {p:.1f}%".format(ap=ap, hp=hp, p=away_win_p * 100))
    #
    #         away_wins_expected = 16 * (away_win_cumul / (len(players[away_home[0]]) * len(players[away_home[1]])))
    #         print("expected wins for {}: {}".format(match.away_team, away_wins_expected))