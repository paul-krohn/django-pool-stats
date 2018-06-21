#!/usr/bin/env python

import argparse
import json
from copy import deepcopy
from math import log

BRACKET_TYPES = ['single', 'double']  # [0] is the default

parser = argparse.ArgumentParser(description='Set up a bracket.')
parser.add_argument(
    '--size',
    type=int,
    help='number of participants in the bracket',
    # required=True,
)
parser.add_argument(
    '--type',
    help='bracket type; default: %(default)s',
    default=BRACKET_TYPES[0],
    choices=BRACKET_TYPES,
)
parser.add_argument(
    '--team-file',
    help='file with one team per line',
    default=None
)

args = parser.parse_args()

# double elimination winners/single elimination bracket

match_rounds = []


def bracket_size(participant_count):
    # the guess is either the correct power of 2, ot 1 less than the correct power of 2
    # if the participant count is equal to 2 ** guess, we are don't need to add 1 to the guess
    guess = int(log(participant_count, 2))
    return 2 ** (guess + int(participant_count != 2 ** guess))


class Match(object):

    def __init__(self, source_match_a, source_match_b, team_a, team_b, id):
        self.source_match_a = source_match_a
        self.source_match_b = source_match_b
        self.team_a = team_a
        self.team_b = team_b
        self.winner = None
        self.id = id

    def teams_desc(self, side):
        if self.team_a and self.team_b:
            description = "winner of {} vs {}".format(self.team_a, self.team_b)
        else:
            description = "{}".format(self.team_a or self.team_b)

        src_m = getattr(self, 'source_match_{}'.format(side), None)
        if src_m is not None:
            description = "winner of match {}".format(self.id)
        return description

    def __repr__(self):

        return("match {}: {} vs {}".format(
            self.id,
            'bye' if self.team_a is False else self.team_a or self.source_match_a.teams_desc('a'),
            'bye' if self.team_b is False else self.team_b or self.source_match_b.teams_desc('b'),
        ))


teams = []
if args.team_file is not None:
    teams = json.load(open(args.team_file))['teams']
    print(json.dumps(teams, indent=2))


if len(teams):
    br_size = bracket_size(len(teams))
else:
    br_size = bracket_size(args.size)

print("the bracket size is: {}".format(bracket_size(br_size)))

# round 1 matches
i = 0
first_round_matches = []
while i < (br_size / 2):
    if len(teams):
        team_a = teams[i]
        team_b = teams[(br_size - 1) - i] if len(teams) > (br_size - 1) - i else False
    else:
        team_a = 'Team {}'.format(i + 1)
        team_b = 'Team {}'.format(br_size - (i))
    first_round_matches.append(
        Match(
            source_match_a=None,
            source_match_b=None,
            team_a=team_a,
            team_b=team_b,
            id=i+1,
        )
    )
    i += 1

running_match_count = i
match_rounds.append(first_round_matches)


def new_round_matches(existing_round_matches, offset):
    these_matches = []
    inc = 0
    while inc < len(existing_round_matches) / 2:
        source_match_a = existing_round_matches[inc]
        source_match_b = existing_round_matches[int(len(existing_round_matches) - inc - 1)]
        these_matches.append(
            Match(
                source_match_a=source_match_a,
                source_match_b=source_match_b,
                team_a=None,
                team_b=None,
                id=offset + inc + 1,
            )
        )
        inc += 1
    return these_matches


round_count = int(log(br_size, 2))

prev_round_matches = first_round_matches

while len(match_rounds) < round_count:
    this_round_match_objects = new_round_matches(
        deepcopy(prev_round_matches), running_match_count
    )
    running_match_count += len(this_round_match_objects)
    match_rounds.append(this_round_match_objects)
    prev_round_matches = this_round_match_objects

for match_round in match_rounds:
    for match in match_round:
        print(match)
