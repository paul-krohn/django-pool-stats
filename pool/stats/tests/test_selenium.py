from django.test import RequestFactory
from django.urls import reverse

from selenium.webdriver.support.ui import Select

from .base_cases import BaseSeleniumPoolStatsTestCase, form_length_map, location_names

from ..models import ScoreSheet, Team
from ..utils import expire_page


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

        # self.selenium.get('{}score_sheet_create/{}/'.format(self.base_url, self.test_match['pk']))
        self.score_sheet_create()

        # test that we get redirected to the edit URL
        self.assertEqual(self.selenium.current_url, '{}score_sheet_edit/{}/'.format(self.base_url, 1))

        for location_name in location_names:
            for form_type in form_length_map:
                # test that we have lineup form for home/away
                lineup_div = self.selenium.find_element_by_id('{}_{}'.format(location_name, form_type))
                lineup_form = lineup_div.find_element_by_tag_name('form')
                lineup_inputs = lineup_form.find_elements_by_tag_name('input')
                # with the correct number of elements
                self.assertEqual(form_length_map[form_type], len(lineup_inputs))
        games_form = self.selenium.find_element_by_name('score_sheet_games_form')
        games_form_inputs = games_form.find_elements_by_tag_name('input')

        # there should be 16 forms in the playoff div; 5 inputs in each is 80 inputs.
        # plus 5 at the top of the form ... plus the submit and game reset button. total is 86.
        self.assertEqual(87, len(games_form_inputs))

    def test_match_create_playoff_scoresheet(self):
        self.score_sheet_create(match_id=self.PLAYOFF_TEST_MATCH_ID, week_id=self.PLAYOFF_TEST_WEEK_ID)
        self.assertEqual(self.selenium.current_url, '{}score_sheet_edit/{}/'.format(self.base_url, 1))
        # <input type="hidden" name="form-TOTAL_FORMS" value="16" id="id_form-TOTAL_FORMS">
        games_form = self.selenium.find_element_by_name('score_sheet_games_form')
        games_form_inputs = games_form.find_elements_by_tag_name('input')
        form_count_input = games_form.find_element_by_id('id_form-TOTAL_FORMS')
        self.assertEqual(int(form_count_input.get_attribute('value')), 17)

        # there should be 17 forms in the playoff div; 5 inputs in each is 85 inputs.
        # plus 5 at the top of the form ... plus the submit and game reset button. total is 92.
        self.assertEqual(92, len(games_form_inputs))

    def test_match_scoresheet_set_lineup(self):
        self.score_sheet_create(match_id=self.PLAYOFF_TEST_MATCH_ID, week_id=self.PLAYOFF_TEST_WEEK_ID)

        self.populate_lineup()
        # now that we have lineups set, make sure we have games, and that all have players. We should still be on the
        # edit page for this scoresheet. then loop over the games form table and check that exactly 2 columns are
        # populated with an <a> element
        games_form = self.selenium.find_element_by_name('score_sheet_games_form')
        games_form_table = games_form.find_element_by_class_name('table')
        table_rows = games_form_table.find_elements_by_class_name('scoresheet-odd') + \
            games_form_table.find_elements_by_class_name('scoresheet-even')
        for table_row in table_rows[0:-1]:  # skip the tie-breaker, which will be the last row
            self.assertEqual(len(table_row.find_elements_by_xpath('td[div[a]]')), 2)

    def test_score_sheet_incomplete_substitution(self):

        self.score_sheet_create(match_id=self.PLAYOFF_TEST_MATCH_ID, week_id=self.PLAYOFF_TEST_WEEK_ID)
        self.populate_lineup()
        score_sheet_id = self.selenium.current_url.split('/')[-2]
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
        self.score_sheet_create(match_id=self.PLAYOFF_TEST_MATCH_ID, week_id=self.PLAYOFF_TEST_WEEK_ID)
        score_sheet_id = self.selenium.current_url.split('/')[-2]

        self.selenium.find_element_by_id('toggle-{}_lineup'.format(location_name)).click()
        lineup_form = self.selenium.find_element_by_id('{}_lineup'.format(location_name))
        for inc in [0, 1]:
            select = Select(lineup_form.find_element_by_id('id_form-{}-player'.format(inc)))
            select.select_by_index(1)  # '1' as the first option in the select is '------' or similar
        # submit the form
        # submit the form
        self.selenium.find_element_by_id('{}_lineup_save'.format(location_name)).click()
        # verify that it redirects to the lineup form on
        self.assertEqual(self.selenium.current_url, '{}score_sheet_lineup/{}/{}'.format(
            self.base_url, score_sheet_id, location_name))

    def test_match_scoresheet_substitutions(self):
        self.score_sheet_create(match_id=self.PLAYOFF_TEST_MATCH_ID, week_id=self.PLAYOFF_TEST_WEEK_ID)

        self.populate_lineup()
        self.set_substitution('away', 11)
        self.set_substitution('home', 11)
        # check that there are 5 players in the summaries
        for location_name in location_names:
            player_summary_div = self.selenium.find_element_by_id('{}-player-summaries'.format(location_name))
            player_summary_table = player_summary_div.find_element_by_tag_name('table')
            player_summary_rows = player_summary_table.find_elements_by_tag_name('tr')
            self.assertEqual(len(player_summary_rows), 6)  # 5 players plus a header row

    def test_scoresheet_duplicate_substitutions(self):
        self.score_sheet_create(match_id=self.PLAYOFF_TEST_MATCH_ID, week_id=self.PLAYOFF_TEST_WEEK_ID)
        score_sheet_id = self.selenium.current_url.split('/')[-2]

        self.set_substitution('away', game_index=11, substitution_index=0)
        self.set_substitution('away', game_index=12, substitution_index=1)  # this creates a duplicate substitution
        self.assertEqual(self.selenium.current_url, '{}score_sheet_substitutions/{}/away'.format(
            self.base_url, score_sheet_id, )
        )

    def test_match_scoresheet_mark_winners(self):
        self.score_sheet_create(match_id=self.PLAYOFF_TEST_MATCH_ID, week_id=self.PLAYOFF_TEST_WEEK_ID)

        self.populate_lineup()
        self.set_substitution('away', 10)
        self.set_substitution('home', 10)
        win_counts = self.set_winners()
        # not sure why it helps here to re-get the same page, but when the game counts come up 8-8, the test fails?
        self.selenium.get('{}score_sheet_edit/{}/'.format(self.base_url, 1))
        for location_name in location_names:
            page_wins = int(self.selenium.find_element_by_id('{}-wins-total'.format(location_name)).text)
            self.assertEqual(
                page_wins,
                win_counts[location_name]
            )

    def test_match_scoresheet_remove_substitutions(self):
        self.score_sheet_create()
        self.populate_lineup()
        self.set_substitution('away', 10)
        self.set_substitution('home', 10)
        for location_name in location_names:
            self.selenium.find_element_by_id('toggle-{}_substitutions'.format(location_name)).click()
            # <input type="checkbox" name="form-0-DELETE" id="id_form-0-DELETE">
            substitution_form = self.selenium.find_element_by_id('{}_substitutions'.format(location_name))
            substitution_form.find_element_by_id('id_form-0-DELETE').click()
            self.selenium.find_element_by_id('{}_substitutions_save'.format(location_name)).click()
        for location_name in location_names:
            player_summary_div = self.selenium.find_element_by_id('{}-player-summaries'.format(location_name))
            player_summary_table = player_summary_div.find_element_by_tag_name('table')
            player_summary_rows = player_summary_table.find_elements_by_tag_name('tr')
            self.assertEqual(len(player_summary_rows), 5)  # 4 players plus a header row

    def test_team_win_totals(self):
        self.score_sheet_create()
        self.populate_lineup()
        self.set_substitution('away', 10)
        self.set_substitution('home', 10)
        # we need the scoresheet id from the current URL
        scoresheet_id = self.selenium.current_url.split('/')[-2]
        win_counts = self.set_winners(forfeits=1, table_runs=2)
        ss = ScoreSheet.objects.get(id=scoresheet_id)
        ss.official = True
        ss.save()

        Team.update_rankings(season_id=self.default_season)
        # expire_page(self.factory.get(reverse('players')), reverse('player', kwargs={'player_id': player.id}))
        expire_page(
            RequestFactory().get(reverse('teams', kwargs={'season_id': self.default_season})),
            reverse('teams', kwargs={'season_id': self.default_season})
        )
        teams = Team.objects.filter(season_id=self.default_season)
        list_of_outcomes = []
        for team in teams:
            list_of_outcomes.append([team.wins(), team.losses()])

        self.assertTrue(list(win_counts.values()) in list_of_outcomes)
