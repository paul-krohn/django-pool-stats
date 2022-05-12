import json

from django.test import RequestFactory
from django.urls import reverse

from selenium.webdriver.support.ui import Select

from .base_cases import BaseSeleniumPoolStatsTestCase, form_length_map, location_names

from ..models import ScoreSheet, Team
from ..utils import page_cache


class BaseViewRedirectTestCase(BaseSeleniumPoolStatsTestCase):

    def test_default_view_redirect(self):
        self.selenium.get(self.base_url)
        self.assertEqual(self.selenium.current_url, '{}teams/{}'.format(self.base_url, self.default_season))

    def test_players_view_redirect(self):
        self.selenium.get('{}players/'.format(self.base_url))
        self.assertEqual(self.selenium.current_url, '{}players/{}'.format(self.base_url, self.default_season))

    def test_divisions_view_redirect(self):
        self.selenium.get('{}divisions/'.format(self.base_url))
        self.assertEqual(self.selenium.current_url, '{}divisions/{}'.format(self.base_url, self.default_season))


class StatusPageTestCase(BaseSeleniumPoolStatsTestCase):

    def test_status_page(self):
        response = self.client.get('{}__status'.format(self.base_url))
        self.assertEqual(response.status_code, 200)


class ScoreSheetTestCase(BaseSeleniumPoolStatsTestCase):

    def setUp(self):
        super(ScoreSheetTestCase, self).setUp()
        self.factory = RequestFactory()

    def test_match_create_scoresheet(self):

        # just tests the lineups and substitutions; games and teams are covered in test_scoresheet

        # self.selenium.get('{}score_sheet_create/{}/'.format(self.base_url, self.test_match['pk']))
        score_sheet_id = self.score_sheet_create()

        # test that we get redirected to the edit URL
        self.assertRegexpMatches(self.selenium.current_url, r'{}score_sheet/\d+/'.format(self.base_url))

        for location_name in location_names:
            for form_type in form_length_map:
                # test that we have lineup form for home/away
                lineup_div = self.selenium.find_element_by_id('{}-{}-content'.format(location_name, form_type))
                lineup_form = lineup_div.find_element_by_tag_name('form')
                lineup_inputs = lineup_form.find_elements_by_tag_name('input')
                # with the correct number of elements
                self.assertEqual(form_length_map[form_type], len(lineup_inputs))

    def test_match_scoresheet_set_lineup(self):
        score_sheet_id = self.score_sheet_create(match_id=self.PLAYOFF_TEST_MATCH_ID, week_id=self.PLAYOFF_TEST_WEEK_ID)

        self.populate_lineup()
        # now that we have lineups set, make sure we have games, and that all have players,
        # except the tie breaker/last game
        summary = self.client.get(
            reverse('score_sheet_summary', kwargs={'score_sheet_id': score_sheet_id})
        )
        score_sheet_summary = json.loads(summary.content.decode())

        for game in score_sheet_summary['games'][0:-1]:
            for loc in location_names:
                self.assertIsNotNone(
                    game['{}_player'.format(loc)]['name']
                )

    def test_score_sheet_incomplete_substitution(self):

        score_sheet_id = self.score_sheet_create(match_id=self.PLAYOFF_TEST_MATCH_ID, week_id=self.PLAYOFF_TEST_WEEK_ID)
        self.populate_lineup()
        arguments = {
            'away_home': 'away',
            'game_index': None,
            'player_index': 1
        }
        self.set_substitution(**arguments)
        self.assertEqual(self.selenium.current_url, '{}score_sheet_substitutions/{}/away'.format(
            self.base_url, score_sheet_id))

    def test_score_sheet_lineup_duplicate_player(self):

        location_name = location_names[0]
        score_sheet_id = self.score_sheet_create(match_id=self.PLAYOFF_TEST_MATCH_ID, week_id=self.PLAYOFF_TEST_WEEK_ID)

        self.selenium.find_element_by_id('toggle-{}_lineup'.format(location_name)).click()
        lineup_form = self.selenium.find_element_by_id('{}-lineup-content'.format(location_name))
        for inc in [0, 1]:
            select = Select(lineup_form.find_element_by_id('id_{}_lineup-{}-player'.format(location_name, inc)))
            select.select_by_index(1)  # '1' as the first option in the select is '------' or similar
        # submit the form
        self.selenium.find_element_by_id('{}_lineup_save'.format(location_name)).click()
        # verify that it redirects to the lineup form on
        self.assertEqual(self.selenium.current_url, '{}score_sheet_lineup/{}/{}'.format(
            self.base_url, score_sheet_id, location_name))

    def test_match_scoresheet_substitutions(self):
        score_sheet_id = self.score_sheet_create(match_id=self.PLAYOFF_TEST_MATCH_ID, week_id=self.PLAYOFF_TEST_WEEK_ID)

        self.populate_lineup()
        self.set_substitution('away', 11)
        self.set_substitution('home', 11)
        # check that there are 5 players in the summaries
        summary = self.client.get(
            reverse('score_sheet_summary', kwargs={'score_sheet_id': score_sheet_id})
        )
        score_sheet_summary = json.loads(summary.content)

        for location_name in location_names:
            self.assertEqual(len(score_sheet_summary['teams'][location_name]['players']), 5)

    def test_scoresheet_duplicate_substitutions(self):
        score_sheet_id = self.score_sheet_create(match_id=self.PLAYOFF_TEST_MATCH_ID, week_id=self.PLAYOFF_TEST_WEEK_ID)

        self.set_substitution('away', game_index=11, substitution_index=0)
        self.set_substitution('away', game_index=12, substitution_index=1)  # this creates a duplicate substitution
        self.assertEqual(self.selenium.current_url, '{}score_sheet_substitutions/{}/away'.format(
            self.base_url, score_sheet_id, )
                         )

    def test_match_scoresheet_mark_winners(self):
        score_sheet_id = self.score_sheet_create(match_id=self.PLAYOFF_TEST_MATCH_ID, week_id=self.PLAYOFF_TEST_WEEK_ID)

        self.populate_lineup()
        self.set_substitution('away', 10)
        self.set_substitution('home', 10)
        win_counts = self.set_winners(scoresheet_id=score_sheet_id)
        # not sure why it helps here to re-get the same page, but when the game counts come up 8-8, the test fails?
        summary = self.client.get(
            reverse('score_sheet_summary', kwargs={'score_sheet_id': score_sheet_id})
        )
        score_sheet_summary = json.loads(summary.content.decode())
        for location_name in location_names:
            self.assertEqual(
                score_sheet_summary['teams'][location_name]['wins'],
                win_counts[location_name]
            )

    def test_match_scoresheet_remove_substitutions(self):
        score_sheet_id = self.score_sheet_create()
        self.populate_lineup()
        self.set_substitution('away', 10)
        self.set_substitution('home', 10)

        summary = self.client.get(
            reverse('score_sheet_summary', kwargs={'score_sheet_id': score_sheet_id})
        )
        score_sheet_summary = json.loads(summary.content)
        for location_name in location_names:
            # check there are 5 players listed
            self.assertEqual(len(score_sheet_summary['teams'][location_name]['players']), 5)
        # remove the subs & re-check
        for location_name in location_names:
            self.selenium.find_element_by_id('toggle-{}_substitutions'.format(location_name)).click()
            # <input type="checkbox" name="form-0-DELETE" id="id_form-0-DELETE">
            substitution_form = self.selenium.find_element_by_id('{}-substitutions-content'.format(location_name))
            substitution_form.find_element_by_id('id_{}_substitutions-0-DELETE'.format(location_name)).click()
            self.selenium.find_element_by_id('{}_substitutions_save'.format(location_name)).click()
        summary = self.client.get(
            reverse('score_sheet_summary', kwargs={'score_sheet_id': score_sheet_id})
        )
        score_sheet_summary = json.loads(summary.content)
        for location_name in location_names:
            # check there are 5 players listed
            self.assertEqual(len(score_sheet_summary['teams'][location_name]['players']), 4)

    def test_team_win_totals(self):
        score_sheet_id = self.score_sheet_create()
        self.populate_lineup()
        self.set_substitution('away', 10)
        self.set_substitution('home', 10)
        win_counts = self.set_winners(forfeits=1, table_runs=2, scoresheet_id=score_sheet_id)
        ss = ScoreSheet.objects.get(id=score_sheet_id)
        ss.official = True
        ss.save()

        Team.update_rankings(season_id=self.default_season)
        page_cache.clear()
        teams = Team.objects.filter(season_id=self.default_season)
        list_of_outcomes = []
        for team in teams:
            list_of_outcomes.append([team.wins, team.losses])

        self.assertTrue(list(win_counts.values()) in list_of_outcomes)
