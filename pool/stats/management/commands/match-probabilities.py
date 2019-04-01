

import itertools
import math
import trueskill

BETA = 0.8  # this is ... a lousy default

from django.core.management.base import BaseCommand

# from trueskill import Rating, rate_1vs1

# from ....stats.models import Player, ScoreSheet, Team
from stats.models import Match, Player, PlayerSeasonSummary, ScoreSheet, Team
# from ....stats.models.globals import away_home


def win_probability(team1, team2):
    # delta_mu = sum(r.mu for r in team1) - sum(r.mu for r in team2)
    # sum_sigma = sum(r.sigma ** 2 for r in itertools.chain(team1, team2))
    # size = len(team1) + len(team2)
    # denom = math.sqrt(size * (BETA * BETA) + sum_sigma)
    # ts = trueskill.global_env()
    # return ts.cdf(delta_mu / denom)
    delta_mu = team1.mu - team2.mu
    sum_sigma = sum(r.sigma ** 2 for r in [team1, team2])
    size = 2  # len(team1) + len(team2)
    denom = math.sqrt(size * (BETA * BETA) + sum_sigma)
    ts = trueskill.global_env()
    return ts.cdf(delta_mu / denom)


class Command(BaseCommand):

    help = 'Calculates players\' trueskill ratings'

    sample_season_summary_id = 802

    def add_arguments(self, parser):
        parser.add_argument('match_id', nargs='+', type=int)

    def handle(self, *args, **options):
        # for match_id in options['match_id']:
        #     match = Match.objects.get(id=match_id)
        #     home_players = match.home_team.players.all()
        #     away_players = match.away_team.players.all()
        #     season = match.season_id
        #
        #     for home_player in home_players:
        #         for away_player in away_players:
        #             home_player_rating = PlayerSeasonSummary.objects.get(player_id=home_player.id, season=season).rating()
        #             away_player_rating = PlayerSeasonSummary.objects.get(player_id=away_player.id, season=season).rating()
        #             win_p = win_probability(home_player_rating, away_player_rating)
        #             print("{} vs {}: {:.3f}".format(home_player, away_player, win_p))
        for match_id in options['match_id']:
            score_sheet = ScoreSheet.objects.get(id=match_id)
            games = score_sheet.games.all()
            # home_players = match.home_team.players.all()
            # away_players = match.away_team.players.all()
            season = score_sheet.match.season_id
            home_cumulative_expected_wins = 0.0

            for game in games:
                home_player_rating = PlayerSeasonSummary.objects.get(player_id=game.home_player.id, season=season).rating()
                away_player_rating = PlayerSeasonSummary.objects.get(player_id=game.away_player.id, season=season).rating()
                win_p = win_probability(home_player_rating, away_player_rating)
                home_cumulative_expected_wins += win_p
                print("{} vs {}: {:.3f}".format(game.home_player, game.away_player, win_p))
            print("home expected wins: {}".format(home_cumulative_expected_wins))
