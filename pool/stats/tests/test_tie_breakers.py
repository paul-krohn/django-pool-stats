from django.urls import reverse

from .base_cases import BasePoolStatsTestCase
from .test_unit import populate_lineup_entries
from ..models import Team, ScoreSheet


class TieBreakerTestCase(BasePoolStatsTestCase):

    def setUp(self):
        super(TieBreakerTestCase, self).setUp()

    def create_score_sheet(self, match_id):
        # create a score sheet with a set number of wins, so we can test
        # forfeit and net wins tie-breakers
        response = self.client.post(reverse('score_sheet_create'), data={'match_id': match_id})
        return int(response.url.split('/')[-2])  # url has a trailing slash

    def test_net_game_tie_break(self):
        score_sheet_id = self.create_score_sheet(self.DEFAULT_TEST_MATCH_ID)
        score_sheet = ScoreSheet.objects.get(id=score_sheet_id)

        # creating the score sheet above creates the lineup entries, now we need to populate them
        populate_lineup_entries(score_sheet)
        # and the games
        score_sheet.set_games()
        # now set winners, 9 - 7 for the home team
        inc = 0
        for game in score_sheet.games.all():
            game.winner = 'home' if inc < 9 else 'away'
            game.save()
            inc += 1
        score_sheet.official = 1
        score_sheet.save()
        # now set up the tie by win pct
        teams = Team.objects.filter(id__in=[score_sheet.match.away_team.id, score_sheet.match.home_team_id])
        for team in teams:
            team.win_percentage = 0.5
            team.save()
        # now find and break the set-up tie
        the_ties = Team.find_ties(teams, 'win_percentage', False, set_rankings=True)
        for a_tie in the_ties:
            a_tie.break_it('net_game_wins_against', False, tie_arg=True, reverse_order=True)

        # we have to re-get the teams; the versions in the tie won't reflect the updated ranking.
        self.assertEqual(Team.objects.get(id=score_sheet.match.home_team.id).ranking, 1)
        self.assertEqual(Team.objects.get(id=score_sheet.match.away_team.id).ranking, 2)

    def test_forfeit_wins_tie_break(self):
        score_sheet_id = self.create_score_sheet(self.DEFAULT_TEST_MATCH_ID)
        score_sheet = ScoreSheet.objects.get(id=score_sheet_id)

        # creating the score sheet above creates the lineup entries, now we need to populate them
        populate_lineup_entries(score_sheet)
        # and the games
        score_sheet.set_games()
        # now set winners, 8 each so the teams are tied, one forfeit
        inc = 0
        for game in score_sheet.games.all():
            if inc == 0:
                game.forfeit = True
            game.winner = 'home' if game.order.order % 2 else 'away'
            game.save()
            inc += 1
        score_sheet.official = 1
        score_sheet.save()
        self.assertEqual(score_sheet.forfeit_wins('away'), 0)
        self.assertEqual(score_sheet.forfeit_wins('home'), 1)

        Team.update_rankings(season_id=self.default_season)
        self.assertEqual(Team.objects.get(id=score_sheet.match.home_team.id).ranking, 2)
        self.assertEqual(Team.objects.get(id=score_sheet.match.away_team.id).ranking, 1)
