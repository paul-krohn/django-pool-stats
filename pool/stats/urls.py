from django.conf.urls import url
from django.views.decorators.cache import cache_page

from . import views, status

urlpatterns = [
    url(r'^$', views.index, name='index'),

    url(r'^divisions/(?P<season_id>[0-9]+)', cache_page(15)(views.divisions), name='divisions'),
    url(r'^divisions/', views.divisions, name='divisions'),

    url(r'^team/(?P<team_id>[0-9]+)/$', views.team, name='team'),

    url(r'^teams/(?P<season_id>[0-9]+)', cache_page(15)(views.teams), name='teams'),
    url(r'^teams/', views.index, name='teams'),

    url(r'^week/(?P<week_id>[0-9]+)/$', views.week, name='week'),
    url(r'^weeks/', views.weeks, name='weeks'),

    url(r'^match/(?P<match_id>[0-9]+)/$', views.match, name='match'),

    url(r'^players/(?P<season_id>[0-9]+)', cache_page(15)(views.players), name='players'),
    url(r'^players/', views.players, name='players'),
    # url(r'^foo/([0-9]{1,2})/$', cache_page(60 * 15)(my_view)),

    url(r'^player/(?P<player_id>[0-9]+)/$', views.player, name='player'),
    url(r'^player_create/', views.player_create, name='player_create'),

    url(r'^sponsors/', views.sponsors, name='sponsors'),
    url(r'^sponsor/(?P<sponsor_id>[0-9]+)/$', views.sponsor, name='sponsor'),

    url(r'^score_sheet_create/(?P<match_id>[0-9]+)/$', views.score_sheet_create, name='score_sheet_create'),
    url(r'^score_sheet_lineup/(?P<score_sheet_id>[0-9]+)/(?P<away_home>[a-z]+)$',
        views.score_sheet_lineup, name='score_sheet_lineup'),
    url(r'^score_sheet_substitutions/(?P<score_sheet_id>[0-9]+)/(?P<away_home>[a-z]+)$',
        views.score_sheet_substitutions, name='score_sheet_substitutions'),

    url(r'^score_sheet_edit/(?P<score_sheet_id>[0-9]+)/$', views.score_sheet_edit, name='score_sheet_edit'),

    url(r'^score_sheet/(?P<score_sheet_id>[0-9]+)/$', views.score_sheet, name='score_sheet'),
    url(r'^score_sheets/', views.score_sheets, name='score_sheets'),

    url(r'^seasons/', views.seasons, name='seasons'),
    url(r'^set_season/(?P<season_id>[0-9]+)/$', views.set_season, name='set_season'),

    url(r'^update_teams_stats/', views.update_teams_stats, name='update_teams_stats'),
    url(r'^update_players_stats/', views.update_players_stats, name='update_players_stats'),

    url(r'^unofficial_results/', views.unofficial_results, name='unofficial_results'),
    url(r'^__status', status.index),

]
