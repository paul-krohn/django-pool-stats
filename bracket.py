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

    def __init__(self, source_match_a, source_match_b, team_a, team_b, number, a_want_winner=True, b_want_winner=True):
        self.source_match_a = source_match_a
        self.source_match_b = source_match_b
        self.team_a = team_a
        self.team_b = team_b
        self.winner = None
        self.number = number
        self.a_want_winner = a_want_winner
        self.b_want_winner = b_want_winner

    def teams_desc(self, side, want):
        if self.team_a and self.team_b:
            description = "{} of {} vs {}".format("winner" if want else "loser", self.team_a, self.team_b)
        else:
            description = "{}".format(self.team_a or self.team_b)

        src_m = getattr(self, 'source_match_{}'.format(side), None)
        if src_m is not None:
            description = "{} of match {}".format("winner" if want else "loser", self.number)
        return description

    def __repr__(self):

        return("match {}: {} vs {}".format(
            self.number,
            'bye' if self.team_a is False else self.team_a or self.source_match_a.teams_desc('a', self.a_want_winner),
            'bye' if self.team_b is False else self.team_b or self.source_match_b.teams_desc('b', self.b_want_winner),
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
        team_one = teams[i]
        team_two = teams[(br_size - 1) - i] if len(teams) > (br_size - 1) - i else False
    else:
        team_one = 'Team {}'.format(i + 1)
        team_two = 'Team {}'.format(br_size - i)
    first_round_matches.append(
        Match(
            source_match_a=None,
            source_match_b=None,
            team_a=team_one,
            team_b=team_two,
            number=i + 1,
        )
    )
    i += 1

running_match_count = i
match_rounds.append(first_round_matches)


def new_round_matches(existing_round_matches, offset):
    these_matches = []
    inc = 0
    while inc < len(existing_round_matches) / 2:
        this_source_match_a = existing_round_matches[inc]
        this_source_match_b = existing_round_matches[int(len(existing_round_matches) - inc - 1)]
        these_matches.append(
            Match(
                source_match_a=this_source_match_a,
                source_match_b=this_source_match_b,
                team_a=None,
                team_b=None,
                number=offset + inc + 1,
            )
        )
        inc += 1
    return these_matches


def losers_bracket_matches(winners_round_matches, offset):
    new_matches = []
    inc = 0
    while inc < len(winners_round_matches) / 2:
        this_source_match_a = winners_round_matches[2 * inc]
        this_source_match_b = winners_round_matches[2 * inc + 1]
        print("adding losers bracket match: {}".format(offset + inc + 1))
        new_matches.append(
            Match(
                source_match_a=this_source_match_a,
                source_match_b=this_source_match_b,
                team_a=None,
                team_b=None,
                number=offset + inc + 1,
                a_want_winner=False,
                b_want_winner=True,
            )
        )
        inc += 1
    return new_matches


round_count = int(log(br_size, 2)) + (1 if args.type == 'double' else 0)

prev_round_matches = first_round_matches
losers_bracket_rounds = []

while len(match_rounds) < round_count:
    # loser's bracket initial round
    print("currently have {} rounds".format(len(match_rounds)))
    if args.type == 'double':
        print("the remainder is: {}".format(len(match_rounds) % 2))
        if (len(match_rounds) % 2) == 1:
            losers_bracket_new_matches = losers_bracket_matches(
                match_rounds[len(match_rounds) - 1],
                running_match_count
            )
            running_match_count += len(losers_bracket_new_matches)
            losers_bracket_rounds.append(losers_bracket_new_matches)
        else:
            # the winner of the prev rd losers bracket, against the losers of the current round winners bracket
            losers_bracket_new_matches = []
            i = 0
            while i < len(match_rounds[-1]):
                winners_source_match = match_rounds[-1][i]
                # source_match_b = losers_bracket_rounds[-1][i]
                losers_source_match = losers_bracket_rounds[-1][len(match_rounds[-1]) - (i + 1)]
                new_match_id = running_match_count + i + 1
                print("setting up match {}; {} from winners bracket and {} from losers".format(
                    new_match_id, winners_source_match.number, losers_source_match.number)
                )
                m = Match(
                    source_match_a=winners_source_match,
                    source_match_b=losers_source_match,
                    team_a=None,
                    team_b=None,
                    number=new_match_id,
                    a_want_winner=False,
                    b_want_winner=True,
                )
                i += 1
                losers_bracket_new_matches.append(m)
            losers_bracket_rounds.append(losers_bracket_new_matches)
            running_match_count += len(losers_bracket_new_matches)

    this_round_match_objects = new_round_matches(
        deepcopy(prev_round_matches), running_match_count
    )
    running_match_count += len(this_round_match_objects)
    match_rounds.append(this_round_match_objects)
    prev_round_matches = this_round_match_objects

for match_round in match_rounds:
    for match in match_round:
        print(match)

print("there are {} losers bracket rounds".format(len(losers_bracket_rounds)))
for losers_bracket_round in losers_bracket_rounds:
    for match in losers_bracket_round:
        print(match)
