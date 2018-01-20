from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.test import Client
from django.test import RequestFactory

from ..models import Season, Player, PlayerSeasonSummary, GameOrder, ScoreSheet, Game

from ..views import get_single_player_view_cache_key, expire_page

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

        # players are cached; make sure we invalidate so we have
        # consistent test results
        cache_key = get_single_player_view_cache_key(
            season_id=Season.objects.get(is_default=True).id,
            player_id=player.id,
        )
        cache.delete(cache_key)

        summary = PlayerSeasonSummary(
            player=player,
            season=Season.objects.get(is_default=True)
        )
        summary.save()

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

        response = self.client.get(reverse('score_sheet_create', kwargs={'match_id': self.sample_match_id}))
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
        response = self.client.get(reverse('score_sheet_create', kwargs={'match_id': self.sample_match_id}))
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
