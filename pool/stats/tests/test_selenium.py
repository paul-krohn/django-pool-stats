from django.test import LiveServerTestCase
from selenium import webdriver
from selenium.webdriver.support.ui import Select

from random import randrange

location_names = ['home', 'away']

form_length_map = {
    'lineup': 10,
    'substitutions': 8
}


class BasePoolStatsTestCase(LiveServerTestCase):

    fixtures = ['sample_seasons', 'sample_game_setup', 'sample_sponsors',
                'sample_players', 'sample_divisions', 'sample_teams', 'sample_weeks',
                'sample_matches']

    default_season = 4

    test_match = {
        "pk": 5,
        "fields": {
            "season": default_season,
            "week": 4,
            "home_team": 6,
            "away_team": 7,
            "playoff": False
        }
    }

    def setUp(self):

        self.selenium = webdriver.Firefox()
        super(BasePoolStatsTestCase, self).setUp()

    def tearDown(self):
        self.selenium.quit()
        super(BasePoolStatsTestCase, self).tearDown()

    def populate_lineup(self):  # name does not contain 'test'; it is used in other tests
        # get the lineup form, set the first player to 1, second to 2, etc
        for location_name in location_names:
            # first, make sure the form you are about to interact with is visible, to avoid a
            # selenium.common.exceptions.ElementNotInteractableException being thrown.
            self.selenium.find_element_by_id('toggle-{}_lineup'.format(location_name)).click()
            lineup_form = self.selenium.find_element_by_id('{}_lineup'.format(location_name))
            for inc in range(0, 4):  # there are 4 play positions; we never do 4 because range() is weird
                select = Select(lineup_form.find_element_by_id('id_form-{}-player'.format(inc)))
                select.select_by_index(inc + 1)  # 'inc + 1' as the first option in the select is '------' or similar
            # submit the form
            self.selenium.find_element_by_id('{}_lineup_save'.format(location_name)).click()

    def set_substitution(self, away_home, index):
        self.selenium.find_element_by_id('toggle-{}_substitutions'.format(away_home)).click()
        substitution_form = self.selenium.find_element_by_id('{}_substitutions'.format(away_home))
        game_select = Select(substitution_form.find_element_by_id('id_form-0-game_order'))
        game_select.select_by_index(index)
        player_select = Select(substitution_form.find_element_by_id('id_form-0-player'))
        # select the 1th player; zero is '------' or similar
        player_select.select_by_index(1)
        selected_player = player_select.first_selected_option
        self.selenium.find_element_by_id('{}_substitutions_save'.format(away_home)).click()
        return selected_player

    def set_winners(self, forfeits=0, table_runs=0):
        games_form = self.selenium.find_element_by_name('score_sheet_games_form')
        # hard-coding game count here, is there a way to not do that?
        # id_form-1-winner_0
        win_counts = {
            'home': 0,
            'away': 0,
        }
        forfeit_games = []
        tr_games = []

        for inc in range(0, 16):
            # choose whether home (0) or away (1) wins "randomly"
            winner = randrange(0, 2)
            win_counts[location_names[winner]] += 1
            button = games_form.find_element_by_id('id_form-{}-winner_{}'.format(inc, winner))
            button.click()
            # set some forfeits!

        while len(forfeit_games) < forfeits:
            candidate = randrange(0, 16)
            while candidate in forfeit_games:
                candidate = randrange(0, 16)
            forfeit_games.append(candidate)
        while len(tr_games) < table_runs:
            candidate = randrange(0, 16)
            while candidate in forfeit_games or candidate in tr_games:
                candidate = randrange(0, 16)
            tr_games.append(candidate)

        for forfeit_game in forfeit_games:
            games_form.find_element_by_id('id_form-{}-forfeit'.format(forfeit_game)).click()
        for tr_game in tr_games:
            games_form.find_element_by_id('id_form-{}-table_run'.format(tr_game)).click()

        games_form.find_element_by_id('games-save-button').click()
        return win_counts

    @property
    def base_url(self):
        return '{}/stats/'.format(self.live_server_url)


class BaseViewRedirectTestCase(BasePoolStatsTestCase):

    def test_default_view_redirect(self):
        self.selenium.get(self.base_url)
        self.assertEquals(self.selenium.current_url, '{}teams/{}'.format(self.base_url, self.default_season))

    def test_players_view_redirect(self):
        self.selenium.get('{}players/'.format(self.base_url))
        self.assertEquals(self.selenium.current_url, '{}players/{}'.format(self.base_url, self.default_season))

    def test_divisions_view_redirect(self):
        self.selenium.get('{}divisions/'.format(self.base_url))
        self.assertEquals(self.selenium.current_url, '{}divisions/{}'.format(self.base_url, self.default_season))


class ScoreSheetTestCase(BasePoolStatsTestCase):

    def test_match_create_scoresheet(self):

        self.selenium.get('{}score_sheet_create/{}/'.format(self.base_url, self.test_match['pk']))

        # test that we get redirected to the edit URL
        self.assertEquals(self.selenium.current_url, '{}score_sheet_edit/{}/'.format(self.base_url, 1))

        for location_name in location_names:
            for form_type in form_length_map:
                # test that we have lineup form for home/away
                lineup_div = self.selenium.find_element_by_id('{}_{}'.format(location_name, form_type))
                lineup_form = lineup_div.find_element_by_tag_name('form')
                lineup_inputs = lineup_form.find_elements_by_tag_name('input')
                # with the correct number of elements
                self.assertEquals(form_length_map[form_type], len(lineup_inputs))
        games_form = self.selenium.find_element_by_name('score_sheet_games_form')
        games_form_inputs = games_form.find_elements_by_tag_name('input')

        # there should be 16 forms in the playoff div; 5 inputs in each is 80 inputs.
        # plus 5 at the top of the form ... plus 1 more somewhere? total is 86.
        self.assertEquals(86, len(games_form_inputs))

    def test_match_create_playoff_scoresheet(self):
        self.selenium.get('{}score_sheet_create/{}/'.format(self.base_url, 11))
        self.assertEquals(self.selenium.current_url, '{}score_sheet_edit/{}/'.format(self.base_url, 1))
        # <input type="hidden" name="form-TOTAL_FORMS" value="16" id="id_form-TOTAL_FORMS">
        games_form = self.selenium.find_element_by_name('score_sheet_games_form')
        games_form_inputs = games_form.find_elements_by_tag_name('input')
        form_count_input = games_form.find_element_by_id('id_form-TOTAL_FORMS')
        self.assertEquals(int(form_count_input.get_attribute('value')), 17)

        # there should be 17 forms in the playoff div; 5 inputs in each is 85 inputs.
        # plus 5 at the top of the form ... plus 1 more somewhere? total is 91.
        self.assertEquals(91, len(games_form_inputs))

    def test_match_scoresheet_set_lineup(self):
        self.selenium.get('{}score_sheet_create/{}/'.format(self.base_url, 11))

        self.populate_lineup()
        # now that we have lineups set, make sure we have games, and that all have players. We should still be on the
        # edit page for this scoresheet. then loop over the games form table and check that exactly 2 columns are
        # populated with an <a> element
        games_form = self.selenium.find_element_by_name('score_sheet_games_form')
        games_form_table = games_form.find_element_by_class_name('table')
        table_rows = games_form_table.find_elements_by_class_name('scoresheet-odd') + \
            games_form_table.find_elements_by_class_name('scoresheet-even')
        for table_row in table_rows[0:-1]:  # skip the tie-breaker, which will be the last row
            self.assertEquals(len(table_row.find_elements_by_xpath('td[div[a]]')), 2)

    def test_match_scoresheet_substitutions(self):
        self.selenium.get('{}score_sheet_create/{}/'.format(self.base_url, 11))

        self.populate_lineup()
        self.set_substitution('away', 11)
        self.set_substitution('home', 11)
        # check that there are 5 players in the summaries
        for location_name in location_names:
            player_summary_div = self.selenium.find_element_by_id('{}-player-summaries'.format(location_name))
            player_summary_table = player_summary_div.find_element_by_tag_name('table')
            player_summary_rows = player_summary_table.find_elements_by_tag_name('tr')
            self.assertEqual(len(player_summary_rows), 6)  # 5 players plus a header row

    def test_match_scoresheet_mark_winners(self):
        self.selenium.get('{}score_sheet_create/{}/'.format(self.base_url, 11))

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
        self.selenium.get('{}score_sheet_create/{}/'.format(self.base_url, 5))
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

    def test_scoresheet_forfeit_win_counts(self):
        """
        Test that when there are forfeits, the teams get credit for the wins, but not the players.
        """

        forfeit_count = 3
        table_run_count = 2

        self.selenium.get('{}score_sheet_create/{}/'.format(self.base_url, 5))
        self.populate_lineup()
        self.set_substitution('away', 10)
        self.set_substitution('home', 10)
        win_counts = self.set_winners(forfeits=3, table_runs=table_run_count)
        self.selenium.get('{}score_sheet_edit/{}/'.format(self.base_url, 1))
        wins_set = 0
        total_wins = 0
        for location_name in location_names:
            wins_set += win_counts[location_name]
            total_wins += int(self.selenium.find_element_by_id('{}-wins-total'.format(location_name)).text)
        self.assertEqual(
            total_wins,
            wins_set
        )
        # add up the player win totals; it should be 16 - forfeit count
        player_wins = 0
        tr_count = 0
        for location_name in location_names:
            player_summary_div = self.selenium.find_element_by_id('{}-player-summaries'.format(location_name))
            player_summary_table = player_summary_div.find_element_by_tag_name('table')
            player_summary_rows = player_summary_table.find_elements_by_tag_name('tr')
            for player_summary_row in player_summary_rows[1:]:  # skip the header row
                player_summary_cells = player_summary_row.find_elements_by_tag_name('td')
                player_wins += int(player_summary_cells[1].text)
                tr_count += int(player_summary_cells[3].text)
        self.assertEqual(player_wins + forfeit_count, 16)
        self.assertEqual(tr_count, table_run_count)
