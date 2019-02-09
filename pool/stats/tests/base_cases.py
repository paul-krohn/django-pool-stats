from django.test import LiveServerTestCase
from selenium.webdriver.support.ui import Select
from selenium.webdriver.firefox.webdriver import WebDriver

from random import randrange
from xvfbwrapper import Xvfb

location_names = ['home', 'away']

form_length_map = {
    'lineup': 10,
    'substitutions': 8
}


class BasePoolStatsTestCase(LiveServerTestCase):

    fixtures = ['sample_seasons', 'sample_game_setup', 'sample_sponsors', 'sample_tables',
                'sample_players', 'sample_divisions', 'sample_teams', 'sample_weeks',
                'sample_matches']

    DEFAULT_TEST_MATCH_ID = 5
    DEFAULT_TEST_WEEK_ID = 5
    DEFAULT_TEST_TABLE_ID = 1

    PLAYOFF_TEST_MATCH_ID = 11
    PLAYOFF_TEST_WEEK_ID = 11

    default_season = 4
    test_match = {
        "pk": DEFAULT_TEST_MATCH_ID,
        "fields": {
            "season": default_season,
            "week": DEFAULT_TEST_WEEK_ID,
            "home_team": 6,
            "away_team": 7,
            "playoff": False
        }
    }

    def setUp(self):

        super(BasePoolStatsTestCase, self).setUp()

    def tearDown(self):

        super(BasePoolStatsTestCase, self).tearDown()


class BaseSeleniumPoolStatsTestCase(BasePoolStatsTestCase):

    def setUp(self):

        self.vdisplay = Xvfb(width=1280, height=1024)
        self.vdisplay.start()
        self.selenium = WebDriver()
        super(BaseSeleniumPoolStatsTestCase, self).setUp()

    def tearDown(self):

        self.selenium.quit()
        self.vdisplay.stop()
        super(BaseSeleniumPoolStatsTestCase, self).tearDown()

    def score_sheet_create(self,
                           match_id=BasePoolStatsTestCase.DEFAULT_TEST_MATCH_ID,
                           week_id=BasePoolStatsTestCase.DEFAULT_TEST_WEEK_ID):
        self.selenium.get('{}week/{}'.format(self.base_url, week_id))
        self.selenium.find_element_by_id('score_sheet_create_button_match_{}'.format(match_id)).click()

    def populate_lineup(self, away_players=4, home_players=4):
        # get the lineup form, set the first player to 1, second to 2, etc
        for location_name in location_names:
            # first, make sure the form you are about to interact with is visible, to avoid a
            # selenium.common.exceptions.ElementNotInteractableException being thrown.
            self.selenium.find_element_by_id('toggle-{}_lineup'.format(location_name)).click()
            lineup_form = self.selenium.find_element_by_id('{}_lineup'.format(location_name))
            # referring to away_players and home_players only via eval() makes them look unused ...
            for inc in range(0, eval('{}_players'.format(location_name))):
                select = Select(lineup_form.find_element_by_id('id_form-{}-player'.format(inc)))
                select.select_by_index(inc + 1)  # 'inc + 1' as the first option in the select is '------' or similar
            # submit the form
            self.selenium.find_element_by_id('{}_lineup_save'.format(location_name)).click()

    def set_substitution(self, away_home, game_index, player_index=1, substitution_index=0):
        self.selenium.find_element_by_id('toggle-{}_substitutions'.format(away_home)).click()
        substitution_form = self.selenium.find_element_by_id('{}_substitutions'.format(away_home))
        game_select = Select(substitution_form.find_element_by_id('id_form-{}-game_order'.format(substitution_index)))
        if game_index is not None:
            game_select.select_by_index(game_index)
        player_select = Select(substitution_form.find_element_by_id('id_form-{}-player'.format(substitution_index)))
        # select the 1th player; zero is '------' or similar
        player_select.select_by_index(player_index)
        selected_player = player_select.first_selected_option
        self.selenium.find_element_by_id('{}_substitutions_save'.format(away_home)).click()
        return selected_player

    def set_winners(self, forfeits=0, table_runs=0, random_wins=True):
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
            if random_wins:
                winner = randrange(0, 2)
            else:
                winner = inc % 2
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

    @staticmethod
    def count_player_stats_in_table(table):

        player_rows = table.find_elements_by_xpath('tbody/tr')
        wins = 0
        losses = 0
        trs = 0
        for player_row in player_rows:
            player_cells = player_row.find_elements_by_tag_name('td')
            wins += int(player_cells[3].text)
            losses += int(player_cells[4].text)
            trs += int(player_cells[7].text)
        return {
            'wins': wins,
            'losses': losses,
            'trs': trs,
        }

    @property
    def base_url(self):
        return '{}/stats/'.format(self.live_server_url)
