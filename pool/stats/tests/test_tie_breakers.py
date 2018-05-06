from django.test import LiveServerTestCase

from ..models import Season, Team, ScoreSheet, Match

from unittest import mock


class ScoreSheetTests(LiveServerTestCase):

    # TODO: test counting forfeit wins, net wins against another team.

    def setUp(self):
        self.season = Season(name='test_season', pub_date='2012-08-01 00:00:00Z', is_default=True)
        self.season.save()
        self.team_a = Team(name='Team A', season=self.season)
        self.team_b = Team(name='Team B', season=self.season)
        self.team_a.win_percentage = 0.5
        self.team_b.win_percentage = 0.5

    def test_net_game_tie_break(self):
        found_ties = Team.find_ties([self.team_a, self.team_b], 'win_percentage', False, set_rankings=True)
        self.team_a.net_game_wins_against = mock.MagicMock(return_value=4)
        self.team_b.net_game_wins_against = mock.MagicMock(return_value=8)
        self.assertEqual(found_ties, [[self.team_a, self.team_b]])

        Team.break_tie(found_ties[0], 'net_game_wins_against', tie_arg=True)
        self.assertEqual(self.team_b.ranking, 2)
        self.assertEqual(self.team_a.ranking, 1)

    def test_forfeit_wins_tie_break(self):
        # first we need to set up the tied situation
        found_ties = Team.find_ties([self.team_a, self.team_b], 'win_percentage', False, set_rankings=True)
        self.team_a.forfeit_wins = mock.MagicMock(return_value=1)
        self.team_b.forfeit_wins = mock.MagicMock(return_value=0)
        self.assertEqual(found_ties, [[self.team_a, self.team_b]])

        Team.break_tie(found_ties[0], 'forfeit_wins')
        self.assertEqual(self.team_b.ranking, 1)
        self.assertEqual(self.team_a.ranking, 2)

    def test_net_game_wins_against(self):

        score_sheet_a = ScoreSheet()
        score_sheet_a.match = Match(away_team=self.team_a, home_team=self.team_b)
        score_sheet_a.away_wins = mock.MagicMock(return_value=7)
        score_sheet_a.home_wins = mock.MagicMock(return_value=9)

        score_sheet_b = ScoreSheet()
        score_sheet_b.match = Match(away_team=self.team_b, home_team=self.team_a)
        score_sheet_b.away_wins = mock.MagicMock(return_value=1)
        score_sheet_b.home_wins = mock.MagicMock(return_value=15)

        self.assertEqual(self.team_a.net_game_wins_against([self.team_b], score_sheets=[score_sheet_a]), -2)
        self.assertEqual(self.team_b.net_game_wins_against([self.team_a], score_sheets=[score_sheet_a]), 2)

        self.assertEqual(self.team_a.net_game_wins_against([self.team_b], score_sheets=[score_sheet_b]), 14)
        self.assertEqual(self.team_b.net_game_wins_against([self.team_a], score_sheets=[score_sheet_b]), -14)

        self.assertEqual(
            self.team_a.net_game_wins_against([self.team_b], score_sheets=[score_sheet_a, score_sheet_b]),
            12
        )
        self.assertEqual(
            self.team_b.net_game_wins_against([self.team_a], score_sheets=[score_sheet_a, score_sheet_b]),
            -12
        )
