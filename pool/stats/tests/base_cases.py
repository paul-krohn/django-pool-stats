import json

from django.test import LiveServerTestCase
from django.urls import reverse

from selenium.webdriver.support.ui import Select
from selenium.webdriver.firefox.webdriver import WebDriver

from random import randrange
from xvfbwrapper import Xvfb

from ..models import Game

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

    DEFAULT_TEST_AWAY_TEAM_ID = 6
    DEFAULT_TEST_HOME_TEAM_ID = 7

    PLAYOFF_TEST_MATCH_ID = 11
    PLAYOFF_TEST_WEEK_ID = 11

    default_season = 4
    test_match = {
        "pk": DEFAULT_TEST_MATCH_ID,
        "fields": {
            "season": default_season,
            "week": DEFAULT_TEST_WEEK_ID,
            "home_team": DEFAULT_TEST_HOME_TEAM_ID,
            "away_team": DEFAULT_TEST_AWAY_TEAM_ID,
            "playoff": False
        }
    }

    def setUp(self):

        super(BasePoolStatsTestCase, self).setUp()
        self.client.session['auto_save'] = True
        self.client.session.save()

    def tearDown(self):

        super(BasePoolStatsTestCase, self).tearDown()


class BaseSeleniumPoolStatsTestCase(BasePoolStatsTestCase):

    def setUp(self):

        self.virtual_display = Xvfb(width=1920, height=1080)
        self.virtual_display.start()
        self.selenium = WebDriver()
        super(BaseSeleniumPoolStatsTestCase, self).setUp()

    def tearDown(self):

        self.selenium.quit()
        self.virtual_display.stop()
        super(BaseSeleniumPoolStatsTestCase, self).tearDown()

    def score_sheet_create(self,
                           match_id=BasePoolStatsTestCase.DEFAULT_TEST_MATCH_ID,
                           week_id=BasePoolStatsTestCase.DEFAULT_TEST_WEEK_ID):
        self.selenium.get('{}week/{}'.format(self.base_url, week_id))
        self.selenium.find_element_by_id('score_sheet_create_button_match_{}'.format(match_id)).click()
        return self.selenium.current_url.split('/')[-2]

    def populate_lineup(self, away_players=4, home_players=4):
        # get the lineup form, set the first player to 1, second to 2, etc
        for location_name in location_names:
            # first, make sure the form you are about to interact with is visible, to avoid a
            # selenium.common.exceptions.ElementNotInteractableException being thrown.
            self.selenium.find_element_by_id('toggle-{}_lineup'.format(location_name)).click()
            lineup_form = self.selenium.find_element_by_id('{}-lineup-content'.format(location_name))
            # referring to away_players and home_players only via eval() makes them look unused ...
            for inc in range(0, eval('{}_players'.format(location_name))):
                select = Select(lineup_form.find_element_by_id('id_{}_lineup-{}-player'.format(location_name ,inc)))
                select.select_by_index(inc + 1)  # 'inc + 1' as the first option in the select is '------' or similar
            # submit the form
            self.selenium.find_element_by_id('{}_lineup_save'.format(location_name)).click()

    def set_substitution(self, away_home, game_index, player_index=1, substitution_index=0):
        self.selenium.find_element_by_id('toggle-{}_substitutions'.format(away_home)).click()
        substitution_form = self.selenium.find_element_by_id('{}-substitutions-content'.format(away_home))
        game_select = Select(substitution_form.find_element_by_id('id_{}_substitutions-{}-game_order'.format(away_home, substitution_index)))
        if game_index is not None:
            game_select.select_by_index(game_index)
        player_select = Select(substitution_form.find_element_by_id('id_{}_substitutions-{}-player'.format(away_home, substitution_index)))
        # select the 1th player; zero is '------' or similar
        player_select.select_by_index(player_index)
        selected_player = player_select.first_selected_option
        self.selenium.find_element_by_id('{}_substitutions_save'.format(away_home)).click()
        return selected_player

    def set_winners(self, forfeits=0, table_runs=0, scoresheet_id=1, random_wins=True):

        summary = self.client.get(
            reverse('score_sheet_summary', kwargs={'score_sheet_id': scoresheet_id})
        )
        score_sheet_summary = json.loads(summary.content)
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
            score_sheet_summary['games'][inc]['winner'] = location_names[winner]

        while len(forfeit_games) < forfeits:
            candidate = randrange(0, 16)
            while candidate in forfeit_games:
                candidate = randrange(0, 16)
            forfeit_games.append(candidate)
            score_sheet_summary['games'][candidate]['forfeit'] = True

        while len(tr_games) < table_runs:
            candidate = randrange(0, 16)
            while candidate in forfeit_games or candidate in tr_games:
                candidate = randrange(0, 16)
            tr_games.append(candidate)
            score_sheet_summary['games'][candidate]['table_run'] = True

        for game in score_sheet_summary['games']:
            db_game = Game.objects.get(id=game['id'])
            db_game.winner = game['winner']
            db_game.table_run = game['table_run']
            db_game.forfeit = game['forfeit']
            db_game.save()

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
