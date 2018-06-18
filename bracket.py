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
    required=True,
)
parser.add_argument(
    '--type',
    help='bracket type; default: %(default)s',
    default=BRACKET_TYPES[0],
    choices=BRACKET_TYPES,
)

args = parser.parse_args()

# double elimination winners/single elimination bracket

matches = []
match_objects = []


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
        description = "winner of {} vs {}".format(self.team_a, self.team_b)
        src_m = getattr(self, 'source_match_{}'.format(side), None)
        if src_m is not None:
            description = "winner of match {}".format(src_m.id)
        return description

    def __repr__(self):
        # print("repr fired")
        return("match {}: {} vs {}".format(
            self.id,
            self.team_a or self.source_match_a.teams_desc('a'),
            self.team_b or self.source_match_b.teams_desc('b'),
        ))


print("the bracket size is: {}".format(bracket_size(args.size)))
br_size = bracket_size(args.size)
# round 1 matches
i = 1
first_round_matches = []
first_round_match_objects = []
while i < (br_size / 2) + 1:
    # first_round_matches.append('{} vs {}'.format(i, br_size - (i - 1)))
    first_round_match_objects.append(
        Match(
            source_match_a=None,
            source_match_b=None,
            team_a='Team {}'.format(i),
            team_b='Team {}'.format(br_size - (i - 1)),
            id=i,
        )
    )
    i += 1

running_match_count = i
match_objects.append(first_round_match_objects)


def new_round_object_matches(existing_round_matches, offset):
    these_matches = []
    inc = 0
    while inc < len(existing_round_matches) / 2:
        these_matches.append(
            Match(
                source_match_a=existing_round_matches[inc],
                source_match_b=existing_round_matches[int(len(existing_round_matches) - inc - 1)],
                team_a=None,
                team_b=None,
                id=offset + inc,
            )
        )
        inc += 1
    return these_matches


round_count = int(log(br_size, 2))

prev_round_match_objects = first_round_match_objects
while len(match_objects) < round_count:
    this_round_match_objects = new_round_object_matches(
        prev_round_match_objects, running_match_count
    )
    running_match_count += len(this_round_match_objects)
    match_objects.append(this_round_match_objects)
    prev_round_match_objects = this_round_match_objects

for match_object_list in match_objects:
    for match_object in match_object_list:
        print(match_object)
