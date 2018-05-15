from django.conf.urls import url
from django.views.decorators.cache import cache_page
from django.conf import settings

from . import views, status
from .views import score_sheet
from .views import week
from .views import player


view_cache_time = settings.VIEW_CACHE_TIME

urlpatterns = [
    url(r'^$', views.index, name='index'),

    url(r'^divisions/(?P<season_id>[0-9]+)', cache_page(view_cache_time)(views.divisions), name='divisions'),
    url(r'^divisions/', views.divisions, name='divisions'),

    # the 'after' parameter is really just to make it testable
    url(r'^team/(?P<team_id>[0-9]+)/(?P<after>[0-9-]+)?$', views.team, name='team'),

    url(r'^teams/(?P<season_id>[0-9]+)', cache_page(view_cache_time)(views.teams), name='teams'),
    url(r'^teams/', views.index, name='teams'),

    url(r'^week/(?P<week_id>[0-9]+)/$', week.week, name='week'),
    url(r'^weeks/', week.weeks, name='weeks'),
    url(r'^nextweek/(?P<today_date>[0-9-]+)', week.get_current_week, name='nextweek'),
    url(r'^nextweek/', week.get_current_week, name='nextweek'),

    url(r'^players/(?P<season_id>[0-9]+)', cache_page(view_cache_time)(player.players), name='players'),
    url(r'^players/', player.players, name='players'),

    url(r'^player/(?P<player_id>[0-9]+)/$', cache_page(view_cache_time)(player.player), name='player'),
    url(r'^player_create/', player.player_create, name='player_create'),

    url(r'^sponsors/', views.sponsors, name='sponsors'),
    url(r'^sponsor/(?P<sponsor_id>[0-9]+)/$', views.sponsor, name='sponsor'),

    url(r'^score_sheet_create/$', score_sheet.score_sheet_create, name='score_sheet_create'),

    url(r'^score_sheet_lineup/(?P<score_sheet_id>[0-9]+)/(?P<away_home>[a-z]+)$',
        score_sheet.score_sheet_lineup, name='score_sheet_lineup'),
    url(r'^score_sheet_substitutions/(?P<score_sheet_id>[0-9]+)/(?P<away_home>[a-z]+)$',
        score_sheet.score_sheet_substitutions, name='score_sheet_substitutions'),

    url(r'^score_sheet_edit/(?P<score_sheet_id>[0-9]+)/$', score_sheet.score_sheet_edit, name='score_sheet_edit'),

    url(r'^score_sheet/(?P<score_sheet_id>[0-9]+)/$', score_sheet.score_sheet, name='score_sheet'),

    url(r'^seasons/', views.seasons, name='seasons'),
    url(r'^set_season/(?P<season_id>[0-9]+)/$', views.set_season, name='set_season'),

    url(r'^update_stats/', views.update_stats, name='update_stats'),

    url(r'^__status', status.index),

]
