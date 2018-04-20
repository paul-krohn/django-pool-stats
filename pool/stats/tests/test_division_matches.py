from django.contrib.auth.models import User
from django.test.client import Client
from django.urls import reverse

from ..models import Team, Match, Week, WeekDivisionMatchup
from .base_cases import BasePoolStatsTestCase


class DivisionMatchTests(BasePoolStatsTestCase):

    TEST_ADMIN_USERNAME = 'test_admin'
    TEST_ADMIN_PASSWORD = 'test_ad$m!in_Pa55'
    TEST_ADMIN_MAIL = 'test.admin@example.com'

    def setUp(self):
        super(DivisionMatchTests, self).setUp()

        # cribbed from: https://stackoverflow.com/questions/3495114/how-to-create-admin-user-in-django-tests-py#3495219
        User.objects.create_superuser(
            self.TEST_ADMIN_USERNAME,
            self.TEST_ADMIN_MAIL,
            self.TEST_ADMIN_PASSWORD,
        )
        self.logged_in_admin_client = Client()
        self.logged_in_admin_client.login(
            username=self.TEST_ADMIN_USERNAME,
            password=self.TEST_ADMIN_PASSWORD
        )

    def test_complete_division_matchup(self):

        the_week = Week.objects.get(pk=7)
        matches = Match.objects.filter(week=the_week)
        self.assertEqual(len(matches), 0)
        # rank the teams ...
        teams = Team.objects.filter(season_id=4).order_by('-pk')

        away_div_id = 11
        home_div_id = 10
        matchup = WeekDivisionMatchup(
            away_division_id=away_div_id,
            home_division_id=home_div_id,
            week=the_week,
        )
        matchup.save()
        division_matchups = WeekDivisionMatchup.objects.filter(week=the_week)
        # print('division matchups for week {}: {}'.format(the_week, division_matchups))
        inc = 1
        for team in teams:
            team.ranking = inc
            # print('team {} is ranked {} and is in division {}'.format(team, team.ranking, team.division))
            team.save()
            inc += 1

        week_admin_url = reverse('admin:stats_week_changelist')
        data = {'action': 'division_matchups', '_selected_action': (the_week.id,)}
        response = self.logged_in_admin_client.post(week_admin_url, data)
        matches = Match.objects.filter(week=the_week)
        self.assertEqual(len(matches), int(len(teams)/2))
        for match in matches:
            self.assertEqual(match.away_team.division.id, away_div_id)
            self.assertEqual(match.home_team.division.id, home_div_id)
