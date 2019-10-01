from unittest.mock import MagicMock

from django.test import LiveServerTestCase, TestCase

from ..models import Bracket, Participant, Round, Tournament, TournamentMatchup


class TournamentLiveTestCases(LiveServerTestCase):


    def test_get_match_loser(self):
        """
        Verify that from the fixture data, we get the correct season as the default.
        """
        p_a = Participant()
        p_b = Participant()
        matchup = TournamentMatchup(
            participant_a=p_a,
            participant_b=p_b,
            winner=p_b,
        )
        print('the not-winner: {}'.format(matchup.not_winner().id))
        self.assertEqual(matchup.not_winner(), matchup.participant_a)


class TournamentTestCases(TestCase):

    def test_matchup_count(self):
        # right_answers is LS round sizes from bracket of 64:
        right_answers = [16, 16, 8, 8, 4, 4, 2, 2, 1]
        t = Tournament()
        t.save()
        b = Bracket(
            tournament=t,
            type='l'
        )
        b.save()

        for inc in range(0, len(right_answers)):
            r = Round(number=inc+1, bracket=b)
            r.bracket.tournament.bracket_size = MagicMock(return_value=64)
            self.assertEqual(right_answers[inc], r.matchup_count())