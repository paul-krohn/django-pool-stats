#!/usr/bin/env python

import argparse
import json
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

    def __init__(self, source_match_a, source_match_b, team_a, team_b):
        self.source_match_a = source_match_a
        self.source_match_b = source_match_b
        self.team_a = team_a
        self.team_b = team_b
        self.winner = None

    def __str__(self):
        return '{} vs {}'.format(self.team_a, self.team_b)

    def __repr__(self):
        return("{} vs {}".format(
            self.team_a or "winner of {}".format(self.source_match_a),
            self.team_b or "winner of {}".format(self.source_match_b),
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
        )
    )
    i += 1

match_objects.append(first_round_match_objects)


def new_round_object_matches(existing_round_matches):
    these_matches = []
    inc = 0
    while inc < len(existing_round_matches) / 2:
        these_matches.append(
            Match(
                source_match_a=existing_round_matches[inc],
                source_match_b=existing_round_matches[int(len(existing_round_matches) - inc - 1)],
                team_a=None,
                team_b=None,
            )

        )
        inc += 1
    return these_matches


prev_round_match_objects = first_round_match_objects
while len(match_objects) < int(log(br_size, 2)):
    this_round_match_objects = new_round_object_matches(prev_round_match_objects)
    match_objects.append(this_round_match_objects)
    prev_round_matches = this_round_match_objects

print(match_objects)
