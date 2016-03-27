import datetime, time
from num2words import num2words
from django.core.urlresolvers import reverse
from django.utils import timezone
from django.test import TestCase
from django.test import Client

from .models import Season, Player, PlayerSeasonSummary, GameOrder, Match, ScoreSheet, Week
from .models import PlayPosition, AwayPlayPosition, HomePlayPosition
from .models import Team, AwayTeam, HomeTeam


match_ups = [
    [1, 1],
    [2, 2],
    [3, 3],

    [1, 2],
    [2, 3],
    [3, 1],

    [1, 3],
    [2, 1],
    [3, 2]
]


def create_season():
    a_season = Season(name='Some Future Season', pub_date=timezone.now(), is_default=True)
    a_season.save()
    return a_season


def create_players(count, start_position):
    inc = 0
    start_position += 65
    players = []
    while inc < count:
        p = Player(first_name=chr(start_position + inc), last_name=chr(start_position + inc + 26))
        p.save()
        players.append(p)
        inc += 1
    return players


def create_teams(a_season):
    """
    14 players to populate 2 teams
    :return:
    """

    team_a = Team(name="Team A", season=a_season)
    team_a.save()
    for p in create_players(7, 0):
        team_a.players.add(p)
    team_a.save()
    team_b = Team(name="Team B", season=a_season)
    team_b.save()
    for p in create_players(7, 16):
        team_b.players.add(p)
    team_b.save()


def create_weeks(a_season, count):
    weeks = []
    inc = 0
    while inc < count:
        (week, created) = Week.objects.get_or_create(
            season=a_season,
            date=timezone.now() + datetime.timedelta(days=7 * inc),
            name='Week {}'.format(chr(65 + inc))
        )
        inc += 1
        week.save()
        weeks.append(week)
    return weeks


def create_play_positions():
    positions = []
    for i in range(1, 4):
        position = PlayPosition(
            home_name="Home Player {}".format(chr(65 + i)),
            away_name="Away Player {}".format(i),
            name="Player {}".format(num2words(i)),
        )
        position.save()
        positions.append(position)
    # one sub position
    positions.append(PlayPosition(
        home_name="Home Sub 1",
        away_name="Away Sub 2",
        name="Sub Two"

    ))
    return positions


def create_game_order():
    """
    Use the 3x3 grid in match_up; tests assumptions about 4x4 grid that may lurk in the code
    :return: bool
    """
    game_match_ups = []
    for match_up in match_ups:
        game_order = GameOrder(
            away_position=AwayPlayPosition.objects.get(name='Player {}'.format(num2words(match_up[0]))),
            home_position=HomePlayPosition.objects.get(name='Player {}'.format(num2words(match_up[1]))),
            name=num2words(len(game_match_ups) + 1),
        )
        game_order.save()
        game_match_ups.append(game_order)
    return game_match_ups


def create_data():
    """
    Create a season, players, 2 teams, and a match, as mock data for many of the tests
    """
    a_season = create_season()
    create_teams(a_season)  # we know they are called Team A and Team B
    create_play_positions()  # we need these in place to test the score sheet creation
    create_game_order()  # these too ...
    (week_one, week_two) = create_weeks(a_season, 2)
    match_one = Match(
        week=week_one,
        season=a_season,
        away_team=AwayTeam.objects.get(name='Team A'),
        home_team=HomeTeam.objects.get(name='Team B'),
    )
    match_one.save()
    return match_one.id


class ScoreSheetTests(TestCase):

    def setUp(self):
        self.sample_match_id = create_data()

    def test_player_index(self):
        """
        Test that a created player is *not* in the player index; as in many
        cases, a default season is required
        """
        # create_test_season()

        player = Player(first_name='George', last_name='Smith')
        player.save()
        response = self.client.get(reverse('players'))
        self.assertQuerysetEqual(response.context['players'], [])

    def test_player_season_summary(self):
        # a_season = create_test_season()
        player = Player(first_name='George', last_name='Smith')
        player.save()
        summary = PlayerSeasonSummary(
            player=player,
            season=Season.objects.get(is_default=True)
        )
        summary.save()
        response = self.client.get(reverse('players'))
        self.assertQuerysetEqual(response.context['players'], ['<PlayerSeasonSummary: PlayerSeasonSummary object>'])

    def test_score_sheet_create(self):
        """
        Create a score sheet, verify you get a redirect to the edit page,
        and that there are the correct number of games attached, and that
        trying to access it via a different session returns a redirect

        """

        response = self.client.get(reverse('score_sheet_create', kwargs={'match_id': self.sample_match_id}))
        # since we have a fresh DB, assume this will be score sheet number 1 ...
        self.assertRedirects(response, expected_url=reverse('score_sheet_edit', kwargs={'score_sheet_id': 1}))

        # the number of games should match the match_ups matrix in create_game_order(), ie 9
        score_sheet = ScoreSheet.objects.get(id=1)
        self.assertEqual(len(score_sheet.games.all()), 9)

        # a second client to test the redirect from another session
        c = Client()
        test_redirect_response = c.get(response.url)
        self.assertRedirects(test_redirect_response, expected_url=reverse('score_sheet', kwargs={'score_sheet_id': 1}))
