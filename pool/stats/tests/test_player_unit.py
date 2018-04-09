from django.urls import reverse
from django.test import RequestFactory

from ..models import Season, Player, PlayerSeasonSummary, Team
from ..views import expire_page
from .base_cases import BasePoolStatsTestCase


class PlayerViewTests(BasePoolStatsTestCase):

    def setUp(self):
        super(PlayerViewTests, self).setUp()
        self.factory = RequestFactory()

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

        # default season is provided by fixtures
        s = Season.objects.get(is_default=True)

        player = Player(first_name='George', last_name='Smith')
        player.save()
        team = Team(
            name='The George Team',
            season=s,
        )
        team.save()
        team.players.add(player)
        team.save()

        summary = PlayerSeasonSummary(
            player=player,
            season=s
        )
        summary.save()
        expire_page(self.factory.get(reverse('players')), reverse('player', kwargs={'player_id': player.id}))

        response = self.client.get(reverse('player', kwargs={'player_id': player.id}))
        self.assertQuerysetEqual(
            response.context['summaries'], ['<PlayerSeasonSummary: George Smith Fall 2010>']
        )
