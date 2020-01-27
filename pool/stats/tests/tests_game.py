from ..models import Game
from .base_cases import BasePoolStatsTestCase


class GameSaveTestCases(BasePoolStatsTestCase):


    def test_save_no_winner(self):
        g = Game()
        g.save()
        self.assertEqual(g.timestamp, None)

    def test_save_winner(self):
        g = Game()
        g.winner = 'home'
        g.save()
        self.assertNotEqual(g.timestamp, None)

    def test_reset_winner(self):

        g = Game()
        g.winner = 'home'
        g.save()
        g.winner = ''
        g.save()
        self.assertEqual(g.timestamp, None)