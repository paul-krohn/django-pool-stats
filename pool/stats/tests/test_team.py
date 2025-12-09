from ..models import Team, ScoreAdjustment

from .base_cases import BasePoolStatsTestCase


class TeamTests(BasePoolStatsTestCase):

    def test_team_win_adjustments(self):

        t = Team(name='whee', season_id=BasePoolStatsTestCase.default_season)
        t.save()
        sa = ScoreAdjustment(team=t)
        sa.wins = 4
        sa.losses = 6
        sa.save()
        self.assertEqual(
            t.score_adjustment['wins'], 4
        )
        self.assertEqual(
            t.score_adjustment['losses'], 6
        )
        t.count_games()
        self.assertEqual(t.wins, 4)
        self.assertEqual(t.losses, 6)
        self.assertEqual(t.win_percentage, 0.4)
