import datetime

from django.urls import reverse
from django.test import Client
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import ValidationError

from ..models import Season, PlayerSeasonSummary, ScoreSheet, Game, Match, Table, Team, Week
from ..models import PlayPosition, AwaySubstitution, HomeSubstitution, GameOrder

from ..utils import expire_page
from ..views.week import get_current_week
from ..views.season import get_default_season
from ..forms import ScoreSheetGameForm
from .base_cases import BasePoolStatsTestCase

import random


def populate_lineup_entries(score_sheet, count=None):
    inc = 0

    if count is None:
        count = len(score_sheet.away_lineup.all())

    while inc < count:
        away_lineup_entry = score_sheet.away_lineup.all()[inc]
        away_lineup_entry.player = score_sheet.match.away_team.players.all()[inc]
        away_lineup_entry.save()
        home_lineup_entry = score_sheet.home_lineup.all()[inc]
        home_lineup_entry.player = score_sheet.match.home_team.players.all()[inc]
        home_lineup_entry.save()
        inc += 1


def add_session_to_request(request):
    """Annotate a request object with a session"""
    middleware = SessionMiddleware()
    middleware.process_request(request)
    request.session.save()


class SeasonTestCases(BasePoolStatsTestCase):

    # this value is assumed given the fixtures
    latest_season_by_date = 5

    def test_get_default_season(self):
        """
        Verify that from the fixture data, we get the correct season as the default.
        """

        self.assertEqual(self.default_season, get_default_season())

    def test_get_default_season_when_no_default(self):
        """
        Verify that when there is no default season, we return the latest one
        """

        default_season = Season.objects.get(id=self.default_season)
        default_season.is_default = False
        default_season.save()

        retrieved_default_season_id = get_default_season()
        self.assertEqual(retrieved_default_season_id, self.latest_season_by_date)

    def test_get_default_season_when_no_seasons(self):
        """
        Verify that when there are no seasons (ie the fixture data seasons
        have been deleted), the default season id is 0.
        """
        for s in Season.objects.all():
            s.delete()
        self.assertEqual(0, get_default_season())


class ScoreSheetTests(BasePoolStatsTestCase):

    def setUp(self):
        super(ScoreSheetTests, self).setUp()
        self.sample_match_id = 5  # match is in fixtures, added above
        self.factory = RequestFactory()
        self.game_count = len(GameOrder.objects.filter(tiebreaker=False))

    def test_score_sheet_create(self):
        """
        Create a score sheet, verify you get a redirect to the edit page,
        and that there are the correct number of games attached, and that
        trying to access it via a different session returns a redirect

        """

        response = self.client.post(reverse('score_sheet_create'), data={'match_id': self.sample_match_id})

        # since we have a fresh DB, assume this will be score sheet number 1 ...
        self.assertRedirects(response, expected_url=reverse('score_sheet_edit', kwargs={'score_sheet_id': 1}))

        # the number of games should match the match_ups matrix in create_game_order(), ie len(match_ups)
        score_sheet = ScoreSheet.objects.get(id=1)
        self.assertEqual(len(score_sheet.games.all()), 16)  # 16 is lineup length squared

        # a second client to test the redirect from another session
        c = Client()
        test_redirect_response = c.get(response.url)
        self.assertRedirects(test_redirect_response, expected_url=reverse('score_sheet', kwargs={'score_sheet_id': 1}))

    def test_score_sheet_set_lineup_with_scored_games(self):
        """
        Create a score sheet, create the lineup,

        """
        test_score_sheet_id = 1
        response = self.client.post(reverse('score_sheet_create'), data={'match_id': self.sample_match_id})
        # since we have a fresh DB, assume this will be score sheet number 1 ...
        self.assertRedirects(
            response,
            expected_url=reverse(
                'score_sheet_edit', kwargs={'score_sheet_id': test_score_sheet_id}
            )
        )
        score_sheet = ScoreSheet.objects.get(id=test_score_sheet_id)

        # creating the score sheet above creates the lineup entries, now we need to populate them
        populate_lineup_entries(score_sheet)
        # and the games
        score_sheet.set_games()
        # now we are ready to test some things
        # in the first game away player should be the team's first player
        self.assertEqual(score_sheet.games.all()[0].away_player, score_sheet.match.away_team.players.all()[0])
        # the last game home player should be the fourth home player
        self.assertEqual(score_sheet.games.last().home_player, score_sheet.match.home_team.players.all()[3])

        inc = 0
        # choose a game at random to be the forfeit
        forfeit_game = random.randint(0, self.game_count)
        # same for a table run, not the same as the forfeit ...
        table_run_game = random.randint(0, self.game_count)
        while table_run_game != forfeit_game:
            table_run_game = random.randint(0, self.game_count)

        away_wins = 0
        home_wins = 0
        away_home = ('away', 'home')
        # this random win setup *eventually* catches all the cases, but it would be better
        # to create ... fixtures? to create all the cases.
        for game in score_sheet.games.all():
            winner = away_home[random.randint(0, 1)]
            game.winner = winner
            if winner == 'away':
                away_wins += 1
            else:
                home_wins += 1
            if inc == table_run_game:
                game.table_run = True
            if inc == forfeit_game:
                game.forfeit = True
            game.save()
            inc += 1

        score_sheet.official = True
        score_sheet.save()

        score_sheet.match.away_team.count_games()
        score_sheet.match.home_team.count_games()

        # forfeit wins count for teams, _count_games does not omit them.
        self.assertEqual(score_sheet.match.away_team.wins(), away_wins)
        self.assertEqual(score_sheet.match.home_team.wins(), home_wins)

        # there should be zero summaries now
        summaries = PlayerSeasonSummary.objects.all()
        self.assertEqual(0, len(summaries))

        season_args = {
            'season_id': Season.objects.get(is_default=True).id,
        }
        update_args = {
            'season_id': Season.objects.get(is_default=True).id,
            'minimum_games': 2,
        }

        PlayerSeasonSummary.update_all(**update_args)
        summaries = PlayerSeasonSummary.objects.all()
        self.assertEqual(37, len(summaries))  # 37 is a magic number, where does that come from?

        # there should now be six players with enough games to be in the standings
        expire_page(self.factory.get(reverse('players')), reverse('players', kwargs=season_args))
        response = self.client.get(reverse('players', kwargs=season_args))
        self.assertEqual(len(response.context['players']), 8)  # 8 is 2x players in lineup

    def test_both_teams_shorthanded(self):

        response = self.client.post(reverse('score_sheet_create'), data={'match_id': self.sample_match_id}, follow=True)

        # the score sheet id is the -2th component when split on /
        ss = ScoreSheet.objects.get(id=int(response.request['PATH_INFO'].split('/')[-2]))

        # how long should the lineups be? add 1 fewer players than that
        lineup_len = len(PlayPosition.objects.filter(tiebreaker=False))
        populate_lineup_entries(ss, lineup_len - 1)

        ss.set_games()

        for game in ss.games.all():
            if game.away_player is None and game.home_player is None:
                continue
            if game.away_player is None:
                game.winner = 'home'
            elif game.home_player is None:
                game.winner = 'away'

            game.winner = 'home' if game.order.order % 2 else 'away'
            game.save()

        self.assertEqual(ss.away_wins(), 7)
        self.assertEqual(ss.home_wins(), 8)

    def test_player_win_totals(self):
        response = self.client.post(reverse('score_sheet_create'), data={'match_id': self.sample_match_id}, follow=True)
        # the score sheet id is the -2th component when split on /
        ss = ScoreSheet.objects.get(id=int(response.request['PATH_INFO'].split('/')[-2]))

        # how long should the lineups be? add 1 fewer players than that
        lineup_len = len(PlayPosition.objects.filter(tiebreaker=False))
        populate_lineup_entries(ss, lineup_len - 1)

        away_players = ss.match.away_team.players.all()
        home_players = ss.match.home_team.players.all()

        away_substitution = AwaySubstitution(
            game_order=GameOrder.objects.get(order=10),
            player=away_players[lineup_len],
            play_position=PlayPosition.objects.get(id=2),
        )
        away_substitution.save()
        ss.away_substitutions.add(
            away_substitution
        )

        home_substitution = HomeSubstitution(
            game_order=GameOrder.objects.get(order=11),
            player=home_players[lineup_len],
            play_position=PlayPosition.objects.get(id=2),
        )
        home_substitution.save()
        ss.home_substitutions.add(home_substitution)

        ss.set_games()
        for game in ss.games.all():
            # print("game {} has away player {} and home player {}".format(game, game.away_player, game.home_player))
            if game.away_player is None and game.home_player is None:
                # print("game {} has no players".format(game))
                continue
            if game.away_player is None:
                game.winner = 'home'
            elif game.home_player is None:
                game.winner = 'away'
            else:
                game.winner = 'home'
            game.save()

        ss.official = 1
        ss.save()

        Team.update_teams_stats(season_id=self.default_season)
        for team in Team.objects.filter(season_id=self.default_season):
            team.count_games()

        PlayerSeasonSummary.update_all(season_id=self.default_season)
        summaries = PlayerSeasonSummary.objects.filter(
            season=self.default_season,
        )
        stats = {
            'wins': 0,
            'losses': 0,
            'trs': 0,
        }
        for summary in summaries:
            # print(summary.wins, summary.losses)
            stats['wins'] += summary.wins
            stats['losses'] += summary.losses
            stats['trs'] += summary.table_runs

        self.assertEqual(stats['wins'], 15)
        self.assertEqual(stats['losses'], 11)

    def test_scoresheet_forfeit_win_counts(self):
        """
        Test that when there are forfeits, the teams get credit for the wins, but not the players.
        """

        forfeit_count = 3

        response = self.client.post(reverse('score_sheet_create'), data={'match_id': self.sample_match_id}, follow=True)
        # the score sheet id is the -2th component when split on /
        ss = ScoreSheet.objects.get(id=int(response.request['PATH_INFO'].split('/')[-2]))

        populate_lineup_entries(ss)
        ss.set_games()
        game_count = len(ss.games.all())
        i = 0
        for game in ss.games.all():
            if i > game_count - (forfeit_count + 1):
                game.forfeit = True
                if game.order.home_breaks:
                    game.winner = 'home'
                else:
                    game.winner = 'away'
            else:
                game.winner = 'home'
            game.save()
            i += 1
        ss.official = 1
        ss.save()

        player_win_counts = {'away': 0, 'home': 0}
        for ah in player_win_counts:
            summaries = ss.player_summaries(ah)
            for x in summaries:
                player_win_counts[ah] += x['wins']

        self.assertEqual(player_win_counts['home'], game_count - forfeit_count)
        self.assertEqual(ss.away_wins() + ss.home_wins(), game_count)

    def test_score_sheet_copy_access(self):
        """
        Test that you can copy a score sheet you don't have access to
        """
        response = self.client.post(reverse('score_sheet_create'), data={'match_id': self.sample_match_id}, follow=True)
        ss = ScoreSheet.objects.get(id=int(response.request['PATH_INFO'].split('/')[-2]))
        # now spin up another client which should get bounced to the view page when it requests the edit page
        c = Client()
        no_access_response = c.get(reverse('score_sheet_edit', kwargs={'score_sheet_id': ss.id}))
        self.assertRedirects(no_access_response, reverse('score_sheet', kwargs={'score_sheet_id': ss.id}))

        # now try to copy the score sheet with the 2nd client
        copy_response = c.post(reverse('score_sheet_copy'), data={'scoresheet_id': ss.id})
        self.assertRedirects(copy_response, reverse('score_sheet_edit', kwargs={'score_sheet_id': ss.id + 1}))

    def test_no_copy_official_score_sheet(self):
        """
        Test that if you try to copy an 'official' score sheet, you get redirected to the view version of the original.
        :return:
        """
        response = self.client.post(reverse('score_sheet_create'), data={'match_id': self.sample_match_id}, follow=True)
        ss = ScoreSheet.objects.get(id=int(response.request['PATH_INFO'].split('/')[-2]))
        ss.official = 1
        ss.save()
        c = Client()
        copy_response = c.post(reverse('score_sheet_copy'), data={'scoresheet_id': ss.id})
        self.assertRedirects(copy_response, reverse('score_sheet',  kwargs={'score_sheet_id': ss.id}))


class GameTests(BasePoolStatsTestCase):

    def test_score_sheet_game_is_tr_and_forfeit(self):

        test_game = Game()
        test_game_form = ScoreSheetGameForm(instance=test_game)
        self.assertEqual(test_game_form.is_valid(), False)  # no data, not valid
        test_game_form = ScoreSheetGameForm({'winner': 'home', 'forfeit': True, 'table_run': False})
        self.assertEqual(test_game_form.is_valid(), True)
        test_game_form = ScoreSheetGameForm({'winner': 'home', 'forfeit': True, 'table_run': True})
        self.assertEqual(test_game_form.is_valid(), False)  # forfeit + tr -> not valid
        self.assertRaises(ValidationError, test_game_form.clean)   # and raises ValidationError


class WeekTests(BasePoolStatsTestCase):

    TEST_WEEKS_COUNT = 7
    TEST_WEEK_5_MATCH_COUNT = 3
    TEST_WEEK_FIRST = 5
    TEST_WEEK_LAST = 11

    def test_weeks_count(self):
        response = self.client.get(reverse('weeks'), follow=True)
        self.assertEqual(len(response.context['weeks']), self.TEST_WEEKS_COUNT)

    def test_week_match_count(self):
        response = self.client.get(reverse('week', kwargs={'week_id': 5}))
        self.assertEqual(len(response.context['unofficial_matches']), self.TEST_WEEK_5_MATCH_COUNT)

    def test_adjacent_weeks(self):
        # week 5 has week 4 previous and week 7 next
        week = Week.objects.get(id=4)
        previous_week = week.previous()
        next_week = week.next()
        self.assertEqual(5, previous_week.id)
        self.assertEqual(7, next_week.id)

    def test_end_weeks(self):
        last_week = Week.objects.get(id=self.TEST_WEEK_LAST)
        self.assertIsNone(last_week.next())
        first_week = Week.objects.get(id=self.TEST_WEEK_FIRST)
        self.assertIsNone(first_week.previous())

    def test_get_next_week_date_after_last_week(self):
        # presumably it is after TEST_WEEK_LAST
        response = self.client.get(reverse('nextweek'))
        self.assertEqual(response.url, '/stats/week/{}/'.format(self.TEST_WEEK_LAST))

    def test_get_next_week_date_before_first_week(self):

        first_week = Week.objects.all().order_by('date').first()
        date_before_first_week = first_week.date - datetime.timedelta(days=1)

        response = self.client.get(reverse('nextweek', kwargs={'today_date': date_before_first_week.strftime('%F')}))
        self.assertEqual(response.url, '/stats/week/{}/'.format(self.TEST_WEEK_FIRST))

    def test_get_next_week(self):
        factory = RequestFactory()
        request = factory.get(reverse('nextweek'))
        add_session_to_request(request)

        # on sunday, I should get the next tuesday
        current_week_from_sunday = get_current_week(request, '2010-08-08')
        self.assertEqual(current_week_from_sunday.url, reverse('week', kwargs={'week_id': 4}))

        # on Wednesday, I should get the Tuesday/night before
        current_week_from_wednesday = get_current_week(request, '2010-08-11')
        self.assertEqual(current_week_from_wednesday.url, reverse('week', kwargs={'week_id': 4}))

        current_week_between_playoff_dates = get_current_week(request, '2010-09-15')
        self.assertEqual(current_week_between_playoff_dates.url, reverse('week', kwargs={'week_id': 10}))

        current_week_on_playoff_dates = get_current_week(request, '2010-09-16')
        self.assertEqual(current_week_on_playoff_dates.url, reverse('week', kwargs={'week_id': 11}))


class TeamTests(BasePoolStatsTestCase):

    TEST_TEAM_ID = 6
    TEST_TEAM_PLAYER_COUNT = 6
    TEST_DEFAULT_SEASON = 4
    TEST_TEAM_COUNT = 6
    TEST_SEASON_START_DATE = '2010-08-09'
    TEST_TEAM_MATCH_COUNT = 3

    def test_team_player_count(self):

        test_team = Team.objects.get(id=self.TEST_TEAM_ID)
        self.assertEqual(len(test_team.players.all()), self.TEST_TEAM_PLAYER_COUNT)

        season_args = {'season_id': Season.objects.get(is_default=True).id}
        PlayerSeasonSummary.update_all(**season_args)
        summaries = PlayerSeasonSummary.objects.filter(
            player_id__in=list([x.id for x in test_team.players.all()]),
            season_id=self.TEST_DEFAULT_SEASON,
        )
        self.assertEqual(len(summaries), self.TEST_TEAM_PLAYER_COUNT)

        # a bit of artful dodging here; in order to purge a page/view from the cache, we need a request pointing
        # at the page ... so create a request object, request the page with it, then delete it from cache, then
        # request it again for the actual test.
        factory = RequestFactory()
        request = factory.get(reverse('team', kwargs={'team_id': self.TEST_TEAM_ID}))
        expire_page(request, reverse('team', kwargs={'team_id': self.TEST_TEAM_ID}))

        response = self.client.get(reverse('team', kwargs={'team_id': self.TEST_TEAM_ID}))
        self.assertEqual(len(response.context['players']), self.TEST_TEAM_PLAYER_COUNT)

    def test_team_count(self):

        response = self.client.get(reverse('teams'))
        self.assertRedirects(response, expected_url=reverse(
            'teams',
            kwargs={'season_id': self.TEST_DEFAULT_SEASON}
        ))

        args = {'season_id': self.TEST_DEFAULT_SEASON}
        full_response = self.client.get(reverse('teams', kwargs=args), follow=True)
        # so really, one might expect the response to have, you know, a context, but ... it doesn't
        self.assertEqual(full_response.request['PATH_INFO'], reverse('teams', kwargs=args))

    def test_team_upcoming_matches(self):
        # see comment in test_team_player_count about purging the cache to make sure response.context is not empty
        request_args = {'team_id': self.TEST_TEAM_ID, 'after': '2010-01-01'}
        factory = RequestFactory()
        request = factory.get(reverse('team', kwargs=request_args))
        expire_page(request, reverse('team', kwargs=request_args))

        response = self.client.get(reverse('team', kwargs=request_args))
        matches = response.context['matches'].all()
        self.assertEqual(self.TEST_TEAM_MATCH_COUNT, len(matches))

        match_count = len(matches)
        for match_number in range(1, match_count):
            self.assertGreater(
                matches[match_number].week.date,
                matches[match_number - 1].week.date
            )


class TestTables(BasePoolStatsTestCase):

    def setUp(self):
        super(TestTables, self).setUp()
        self.t1 = Team(season_id=self.default_season)
        self.t2 = Team(season_id=self.default_season, table_id=self.DEFAULT_TEST_TABLE_ID)
        self.test_override_table = Table.objects.get(id=2)

    def test_no_table_set(self):

        self.assertEqual(self.t1.table, None)

    def test_match_table_set(self):
        # t1 = Team(season_id=self.default_season)
        # t2 = Team(season_id=self.default_season, table_id=self.DEFAULT_TEST_TABLE)

        m = Match(home_team=self.t2, away_team=self.t1, week_id=self.PLAYOFF_TEST_MATCH_ID)
        self.assertEqual(m.table(), Table.objects.get(id=self.DEFAULT_TEST_TABLE_ID))

    def test_match_override_table(self):

        m = Match(
            home_team=self.t2,
            away_team=self.t1,
            week_id=self.PLAYOFF_TEST_MATCH_ID,
            alternate_table=self.test_override_table,
        )

        self.assertEqual(m.table(), self.test_override_table)
