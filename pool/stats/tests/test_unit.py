from django.core.cache import cache
from django.urls import reverse
from django.test import Client
from django.test import RequestFactory

from ..models import Season, Player, PlayerSeasonSummary, GameOrder, ScoreSheet, Game, Team, Week

from ..views import expire_page


from ..forms import ScoreSheetGameForm
from django.core.exceptions import ValidationError

from .base_cases import BasePoolStatsTestCase

import random


def populate_lineup_entries(score_sheet):
    inc = 0
    for away_lineup_entry in score_sheet.away_lineup.all():
        away_lineup_entry.player = score_sheet.match.away_team.players.all()[inc]
        away_lineup_entry.save()
        inc += 1

    inc = 0
    for home_lineup_entry in score_sheet.home_lineup.all():
        home_lineup_entry.player = score_sheet.match.home_team.players.all()[inc]
        home_lineup_entry.save()
        inc += 1


class ScoreSheetTests(BasePoolStatsTestCase):

    def setUp(self):
        super(ScoreSheetTests, self).setUp()
        self.sample_match_id = 5  # match is in fixtures, added above
        self.factory = RequestFactory()
        self.game_count = len(GameOrder.objects.filter(tiebreaker=False))

    def test_player_index(self):
        """
        Test that a created player is *not* in the player index; as in many
        cases, a default season is required
        """
        player = Player(first_name='George', last_name='Smith')
        player.save()

        url_args = {'season_id':  Season.objects.get(is_default=True).id}
        expire_page(self.factory.get(reverse('players')), reverse(
            'players',
            kwargs=url_args,
        ))

        response = self.client.get(reverse('players', kwargs=url_args))
        self.assertQuerysetEqual(response.context['players'], [])

    def test_player_season_summary(self):

        player = Player(first_name='George', last_name='Smith')
        player.save()

        summary = PlayerSeasonSummary(
            player=player,
            season=Season.objects.get(is_default=True)
        )
        summary.save()
        expire_page(self.factory.get(reverse('players')), reverse('player', kwargs={'player_id': player.id}))

        response = self.client.get(reverse('player', kwargs={'player_id': player.id}))
        self.assertQuerysetEqual(
            response.context['summaries'], ['<PlayerSeasonSummary: George Smith Fall 2010>']
        )

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
        self.assertEquals(0, len(summaries))

        season_args = {'season_id': Season.objects.get(is_default=True).id}

        PlayerSeasonSummary.update_all(**season_args)
        summaries = PlayerSeasonSummary.objects.all()
        self.assertEquals(37, len(summaries))  # 37 is a magic number, where does that come from?

        # there should now be six players with enough games to be in the standings
        expire_page(self.factory.get(reverse('players')), reverse('players', kwargs=season_args))
        response = self.client.get(reverse('players', kwargs=season_args))
        self.assertEqual(len(response.context['players']), 8)  # 8 is 2x players in lineup


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

    def test_get_next_week_no_matching_weeks(self):
        response = self.client.get(reverse('nextweek'))
        self.assertEqual(response.url, '/stats/weeks/')


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

        response = self.client.get(reverse('teams'), follow=True)
        self.assertRedirects(response, expected_url=reverse(
            'teams',
            kwargs={'season_id': self.TEST_DEFAULT_SEASON}
        ))
        self.assertEqual(len(response.context['teams']), self.TEST_TEAM_COUNT)

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
