import json

from django.urls import reverse

from .base_cases import BasePoolStatsTestCase


# non-selenium scoresheet tests
class ScoreSheetTests(BasePoolStatsTestCase):

    def score_sheet_create(
            self,
            match_id=BasePoolStatsTestCase.DEFAULT_TEST_MATCH_ID,
        ):
        response = self.client.post(reverse('score_sheet_create'), data={
            'match_id': match_id,
        })
        return int(response.url.split('/')[-2])

    def test_match_create_scoresheet(self):

        score_sheet_id = self.score_sheet_create()
        summary = self.client.get(
            reverse('score_sheet_summary', kwargs={'score_sheet_id': score_sheet_id})
        )
        score_sheet_summary = json.loads(summary.content)

        # there should be 16 games
        self.assertEqual(len(score_sheet_summary['games']), 16)
        # and 2 teams
        self.assertEqual(len(score_sheet_summary['teams']), 2)

    def test_match_create_playoff_scoresheet(self):

        score_sheet_id = self.score_sheet_create(match_id=self.PLAYOFF_TEST_MATCH_ID)
        summary = self.client.get(
            reverse('score_sheet_summary', kwargs={'score_sheet_id': score_sheet_id})
        )
        score_sheet_summary = json.loads(summary.content)

        # there should be 16 games
        self.assertEqual(len(score_sheet_summary['games']), 17)
        # and 2 teams
        self.assertEqual(len(score_sheet_summary['teams']), 2)
        # and the last game position should br 'TB'
        self.assertEqual(score_sheet_summary['games'][-1]['order']['away_position'], 'TB')
        self.assertEqual(score_sheet_summary['games'][-1]['order']['home_position'], 'TB')
