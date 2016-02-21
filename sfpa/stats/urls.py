from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^team/(?P<team_id>[0-9]+)/$', views.team, name='team'),
    url(r'^teams/', views.index, name='teams'),
    url(r'^seasons/', views.seasons, name='seasons'),
    url(r'^set_season/(?P<season_id>[0-9]+)/$', views.set_season, name='set_season'),

]
