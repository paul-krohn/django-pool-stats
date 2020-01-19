from django.conf.urls import url
from django.views.decorators.cache import cache_page
from django.conf import settings

from . import views, status

from .views import division
from .views import feature
from .views import game
from .views import score_sheet
from .views import week
from .views import matchup
from .views import player
from .views import season
from .views import sponsor
from .views import team
from .views import tournament


view_cache_time = settings.VIEW_CACHE_TIME

urlpatterns = [
    url(r'^$', views.index, name='index'),

    url(r'^feature/$', feature.index, name='feature'),
    url(r'^feature/(?P<feature>[\w]+)/(?P<setting>[\w]+)', feature.save, name='feature_set'),

    url(r'^divisions/(?P<season_id>[0-9]+)', division.divisions, name='divisions'),
    url(r'^divisions/', division.divisions, name='divisions'),

    url(r'^game_update/$', game.update, name='game_update'),

    # the 'after' parameter is really just to make it testable
    url(r'^team/(?P<team_id>[0-9]+)/(?P<after>[0-9-]+)?$', team.team, name='team'),
    url(r'^team/(?P<team_id>[0-9]+)/', team.team, name='team'),
    url(r'^team/register/(?P<team_id>[0-9]+)', team.register, name='register'),
    url(r'^team/register', team.register, name='register'),


    url(r'^teams/(?P<season_id>[0-9]+)', team.teams, name='teams'),
    url(r'^teams/', views.index, name='teams'),

    url(r'^week/(?P<week_id>[0-9]+)/$', week.week, name='week'),
    url(r'^weeks/', week.weeks, name='weeks'),
    url(r'^nextweek/(?P<today_date>[0-9-]+)', week.get_current_week, name='nextweek'),
    url(r'^nextweek/', week.get_current_week, name='nextweek'),

    url(r'^matchup/', matchup.matchup, name='matchup'),

    url(r'^players/(?P<season_id>[0-9]+)', player.players, name='players'),
    url(r'^players/', player.players, name='players'),

    url(r'^player/(?P<player_id>[0-9]+)/(?P<season_id>[0-9]+)/$',
        player.player, name='player'),
    url(r'^player/(?P<player_id>[0-9]+)/$', player.player, name='player'),
    url(r'^player_elo/(?P<player_id>[0-9]+)/$', player.player_elo, name='player_elo'),
    url(r'^player_create/', player.player_create, name='player_create'),

    url(r'^sponsors/', sponsor.sponsors, name='sponsors'),
    url(r'^sponsor/(?P<sponsor_id>[0-9]+)/$', sponsor.sponsor, name='sponsor'),

    url(r'^score_sheet_create/$', score_sheet.score_sheet_create, name='score_sheet_create'),
    url(r'^score_sheet_copy/$', score_sheet.score_sheet_copy, name='score_sheet_copy'),

    url(r'^score_sheet_lineup/(?P<score_sheet_id>[0-9]+)/(?P<away_home>[a-z]+)$',
        score_sheet.score_sheet_lineup, name='score_sheet_lineup'),
    url(r'^score_sheet_substitutions/(?P<score_sheet_id>[0-9]+)/(?P<away_home>[a-z]+)$',
        score_sheet.score_sheet_substitutions, name='score_sheet_substitutions'),

    url(r'^score_sheet_edit/(?P<score_sheet_id>[0-9]+)/$', score_sheet.score_sheet_edit, name='score_sheet_edit'),

    url(r'^score_sheet/(?P<score_sheet_id>[0-9]+)/$', score_sheet.score_sheet, name='score_sheet'),
    url(r'^score_sheet/summary/(?P<score_sheet_id>[0-9]+)/$', score_sheet.score_sheet_summary, name='score_sheet_summary'),

    url(r'^seasons/', season.seasons, name='seasons'),
    url(r'^set_season/(?P<season_id>[0-9]+)/$', season.set_season, name='set_season'),

    url(r'^tournaments/(?P<season_id>[0-9]+)', cache_page(view_cache_time)(tournament.tournaments), name='tournaments'),
    url(r'^tournaments/', tournament.tournaments, name='tournaments'),
    url(r'^tournament/(?P<tournament_id>[0-9]+)/json', tournament.tournament,  {'json': True}, name='tournament_json'),
    url(r'^tournament/(?P<tournament_id>[0-9]+)', tournament.tournament, name='tournament'),
    url(r'^tournament_edit/(?P<tournament_id>[0-9]+)', tournament.tournament_edit, name='tournament_edit'),
    url(r'^tournament_edit/', tournament.tournament_edit, name='tournament_edit'),
    url(r'^tournament_brackets/(?P<tournament_id>[0-9]+)', tournament.tournament_brackets, name='tournament_brackets'),
    url(r'^tournament_mark_winner/', tournament.tournament_mark_winner, name='tournament_mark_winner'),
    url(r'^tournament_participants/(?P<tournament_id>[0-9]+)', tournament.tournament_participants, name='tournament_participants'),
    url(r'^tournament_controls/(?P<tournament_id>[0-9]+)', tournament.tournament_controls, name='tournament_controls'),


    url(r'^__status', status.index),

]
