from datetime import date

from ..models import Season

from .base_cases import BasePoolStatsTestCase


class PlayerViewTests(BasePoolStatsTestCase):

    def test_standings_minimum_games(self):
        s = Season.objects.get(is_default=True)
        # in the fixtures, the second week is "2010-09-07", so we count the
        # weeks ending a day after that; there are 2 weeks with matches in them,
        # so we want the minimum games to be 2
        self.assertEqual(
            s.standings_minimum_games(before_date=date(year=2010, month=9, day=8)), 2
        )


    def test_standings_minimum_games_playoffs(self):
        s = Season.objects.get(is_default=True)
        # in the fixtures, the playoff week is "2010-09-16", so we count the
        # weeks ending a day after that; there are 2 weeks with non-playoff matches in them,
        # so we want the minimum games to be 2
        self.assertEqual(
            s.standings_minimum_games(before_date=date(year=2010, month=9, day=17)), 2
        )
