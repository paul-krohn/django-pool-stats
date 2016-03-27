#!/usr/bin/env python

import csv
import argparse
import os
import random
import sys
import time

if __name__ == '__main__':
    sys.path.append(os.getcwd())
    sys.path.append(os.sep.join([os.getcwd(), 'sfpa']))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sfpa.settings")

# from django.db import models

import django
django.setup()

# from stats.models import Season, Sponsor, Team, Week, Division, Game, Match, Player
# from sfpa.stats.models import AwayLineupEntry, GameOrder, HomeLineupEntry, Player
from stats.models import Player, Season, Division, Team, Sponsor, Match, Week
from stats.models import AwayTeam, HomeTeam

from stats.tests import create_game_order, create_play_positions, create_weeks

parser = argparse.ArgumentParser()
parser.add_argument('csv_file')

args = parser.parse_args()

random.seed(time.time())


def add_sponsors():
    # borrowed from http://www.readersdoglist.com/pubnames.html
    sponsor_names = [
        'The Bofors Gun And Giblets',
        'The Bull And Politician',
        'The Auntie Semitist',
        'The Horse\'s Replacement',
        'The Dog\'s Breakfast',
        'The Human Leg',
        'The Load Of Do',
        'The Stool & Urinal'
    ]
    for sponsor_name in sponsor_names:
        (created, s) = Sponsor.objects.get_or_create(name=sponsor_name)


def add_players(count=128):
    current_players = Player.objects.all()
    if len(current_players) >= count:
        return True
    f = open(args.csv_file)
    reader = csv.DictReader(f)
    input_players = []
    for row in reader:
        input_players.append(row)

    selected_players = random.sample(input_players, count - len(current_players))
    for selected_player in selected_players:
        p = Player(
            first_name=selected_player['first_name'],
            last_name=selected_player['last_name'],
        )
        p.save()


def add_seasons():
    # two seasons, one for now-ish, set as the default, and one for six months ago
    Season.objects.get_or_create(
        name='Spring 2014',
        pub_date='2014-01-15T12:00:00Z',
        is_default=False
    )
    Season.objects.get_or_create(
        name='Fall 2014',
        pub_date='2014-08-15T12:00:00Z',
        is_default=True
    )


def add_teams_and_divisions():
    player_ids = [x.id for x in Player.objects.all()]
    sponsor_ids = [x.id for x in Sponsor.objects.all()]

    divisions = {
        'One': [
            'Padres', 'Cardinals', 'Nationals', 'Phillies'
        ],
        'Two': [
            'Cubs', 'Dodgers', 'Mets', 'Diamondbacks'
        ],
        'Three': [
            'Indians', 'White Sox', 'Devil Rays', 'Angels'
        ],
        'Four': [
            'Royals', 'Rangers', 'Orioles', 'Mariners'
        ]
    }
    for division_name in divisions.keys():
        (d, created) = Division.objects.get_or_create(
            name=division_name,
            season=Season.objects.get(is_default=True)
        )
        for team_name in divisions[division_name]:
            (t, created) = Team.objects.get_or_create(
                name=team_name,
                season=Season.objects.get(is_default=True),
                division=d,
            )
            # add 4-7 players
            if created:
                t.sponsor = Sponsor.objects.get(
                    id=sponsor_ids[random.randrange(0, len(sponsor_ids) - 1)]
                )
                target_team_size = random.randint(4, 7)
                while len(t.players.all()) < target_team_size:
                    t.players.add(Player.objects.get(id=player_ids.pop(random.randint(0, len(player_ids) - 1))))
                    t.save()


def create_matches():
    divisions = Division.objects.all()

    # first, the intra-division weeks
    for division in divisions:
        teams = Team.objects.filter(division=division)
        # week 1: 1v2, 3v4
        (m, created) = Match.objects.get_or_create(
            away_team=AwayTeam.objects.get(id=teams[0].id),
            home_team=HomeTeam.objects.get(id=teams[1].id),
            week=Week.objects.get(name='Week A'),
            season=Season.objects.get(is_default=True)
        )
        (m, created) = Match.objects.get_or_create(
            away_team=AwayTeam.objects.get(id=teams[2].id),
            home_team=HomeTeam.objects.get(id=teams[3].id),
            week=Week.objects.get(name='Week A'),
            season=Season.objects.get(is_default=True)
        )
        (m, created) = Match.objects.get_or_create(
            away_team=AwayTeam.objects.get(id=teams[0].id),
            home_team=HomeTeam.objects.get(id=teams[2].id),
            week=Week.objects.get(name='Week B'),
            season=Season.objects.get(is_default=True)
        )
        (m, created) = Match.objects.get_or_create(
            away_team=AwayTeam.objects.get(id=teams[1].id),
            home_team=HomeTeam.objects.get(id=teams[3].id),
            week=Week.objects.get(name='Week B'),
            season=Season.objects.get(is_default=True)
        )
        (m, created) = Match.objects.get_or_create(
            away_team=AwayTeam.objects.get(id=teams[0].id),
            home_team=HomeTeam.objects.get(id=teams[3].id),
            week=Week.objects.get(name='Week C'),
            season=Season.objects.get(is_default=True)
        )
        (m, created) = Match.objects.get_or_create(
            away_team=AwayTeam.objects.get(id=teams[1].id),
            home_team=HomeTeam.objects.get(id=teams[2].id),
            week=Week.objects.get(name='Week C'),
            season=Season.objects.get(is_default=True)
        )


def main():
    add_players()
    add_sponsors()
    add_seasons()
    add_teams_and_divisions()
    create_weeks(
        a_season=Season.objects.get(is_default=True),
        count=6
    )
    # create_play_positions()
    # create_game_order()
    create_matches()

if __name__ == '__main__':
    sys.path.append(os.getcwd())

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings")
    main()
