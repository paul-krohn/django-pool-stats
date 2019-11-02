from unittest.mock import MagicMock

from django.test import Client, LiveServerTestCase, TestCase
from django.urls import reverse

from .base_cases import BasePoolStatsTestCase

from ..models import Bracket, Participant, Round, Tournament, TournamentMatchup


class TournamentLiveTestCases(LiveServerTestCase):

    def test_get_match_loser(self):
        """
        Verify that we get the loser of a matchup.
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


class TestsWithSampleData(BasePoolStatsTestCase):

    def test_non_owned_tournament_redirect(self):
        response = self.client.post(reverse('tournament_edit'), data={
            'name': 'test team double tournament',
            'type': 'teams',
            'elimination': 'double',
        })

        c = Client()
        test_redirect_response = c.get(response.url)
        self.assertRedirects(test_redirect_response, expected_url=reverse('tournament', kwargs={'tournament_id': 1}))


class TournamentTestCases(TestCase):

    def test_matchup_count(self):
        # right_answers is overall bracket size and first 9 LS bracket sizes for 64 and 1024 participants
        right_answers = [{
            'participants': 64,
            'bracket_sizes': [16, 16, 8, 8, 4, 4, 2, 2, 1],
        },
        {
            'participants': 1024,
            'bracket_sizes': [256, 256, 128, 128, 64, 64, 32, 32, 16],

        }]

        t = Tournament()
        t.save()
        b = Bracket(
            tournament=t,
            type='l'
        )
        b.save()

        for answer_set in right_answers:

            for inc in range(0, len(answer_set['bracket_sizes'])):
                r = Round(number=inc+1, bracket=b)
                r.bracket.tournament.bracket_size = MagicMock(return_value=answer_set['participants'])
                self.assertEqual(answer_set['bracket_sizes'][inc], r.matchup_count())
