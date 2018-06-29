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
        self.play_order = 0

    def teams_desc(self, side, want):
        if self.team_a and self.team_b:
            description = "{} of {} vs {}".format("winner" if want else "loser", self.team_a, self.team_b)
        else:
            description = "{}".format(self.team_a or self.team_b)

        src_m = getattr(self, 'source_match_{}'.format(side), None)
        if src_m is not None:
            description = "{} of match {}".format("winner" if want else "loser", self.play_order)
        return description

    def __repr__(self):

        return("match {}: {} vs {}".format(
            self.play_order,
            'bye' if self.team_a is False else self.team_a or self.source_match_a.teams_desc('a', self.a_want_winner),
            'bye' if self.team_b is False else self.team_b or self.source_match_b.teams_desc('b', self.b_want_winner),
        ))


teams = []
if args.team_file is not None:
    teams = json.load(open(args.team_file))['teams']
    # print(json.dumps(teams, indent=2))


if len(teams):
    br_size = bracket_size(len(teams))
else:
    br_size = bracket_size(args.size)

# print("the bracket size is: {}".format(bracket_size(br_size)))

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


def new_round_matches(existing_round_matches, offset, winners=True, outside_in=True):
    these_matches = []
    inc = 0
    size = len(existing_round_matches)
    while inc < size / 2:
        if outside_in:
            this_source_match_a = existing_round_matches[inc]
            this_source_match_b = existing_round_matches[size - inc - 1]
        else:
            this_source_match_a = existing_round_matches[2 * inc - size]
            this_source_match_b = existing_round_matches[2 * inc - size + 1]
        these_matches.append(
            Match(
                source_match_a=this_source_match_a,
                source_match_b=this_source_match_b,
                team_a=None,
                team_b=None,
                number=offset + inc + 1,
                a_want_winner=winners,
                b_want_winner=winners,
            )
        )
        inc += 1
    return these_matches


def losers_bracket_matches(winners_round_matches, losers_round_matches, offset, reverse=False):
    new_matches = []
    inc = 0
    size = len(winners_round_matches)
    while inc < size:
        # print("adding losers bracket match: {}".format(offset + inc + 1))
        this_source_match_a = winners_round_matches[size - 1 - inc] if reverse else winners_round_matches[inc]
        this_source_match_b = losers_round_matches[inc]
        new_matches.append(
            Match(
                source_match_a=this_source_match_a,
                source_match_b=this_source_match_b,
                team_a=None,
                team_b=None,
                number=offset + size - inc if reverse else offset + inc + 1,
                a_want_winner=False,
                b_want_winner=True,
            )
        )
        inc += 1
    return new_matches


round_count = int(log(br_size, 2))  # + (2 if args.type == 'double' else 0)

prev_round_matches = first_round_matches
losers_bracket_rounds = []

while len(match_rounds) < round_count:
    # loser's bracket initial round
    # print("currently have {} rounds".format(len(match_rounds)))

    this_round_match_objects = new_round_matches(
        deepcopy(prev_round_matches), running_match_count
    )
    running_match_count += len(this_round_match_objects)
    match_rounds.append(this_round_match_objects)
    prev_round_matches = this_round_match_objects

if args.type == 'double':

    # there are log(n, 2) + (log(n, 2) / 2) rounds in the losers bracket
    losers_bracket_round_count = round_count + round_count / 2
    # first, seed the losers bracket
    losers_bracket_rounds.append(new_round_matches(
            existing_round_matches=match_rounds[0],
            offset=running_match_count,
            winners=False,
        )
    )
    running_match_count += len(losers_bracket_rounds[-1])

    # while len(losers_bracket_rounds) < losers_bracket_round_count:
    for match_round in match_rounds[1:-1]:
        # losers_bracket_new_matches = []
        # reverse_it = True if (len(losers_bracket_rounds) + 1) % 4 != 0 else False
        losers_bracket_dropin_matches = losers_bracket_matches(
            winners_round_matches=match_round,
            losers_round_matches=losers_bracket_rounds[-1],
            offset=running_match_count,
            reverse=True,
        )
        losers_bracket_rounds.append(losers_bracket_dropin_matches)
        running_match_count += len(losers_bracket_dropin_matches)
        # in this case, we want a regular elimination bracket from the previous round of the losers bracket
        losers_bracket_elimination_matches = new_round_matches(
            existing_round_matches=losers_bracket_rounds[-1],
            offset=running_match_count,
            outside_in=False,
        )

        running_match_count += len(losers_bracket_elimination_matches)
        losers_bracket_rounds.append(losers_bracket_elimination_matches)
    # one more losers bracket round; this one between the winner of the losers bracket and the loser of the last match
    # of the winners
    losers_bracket_last_round = losers_bracket_matches(
        winners_round_matches=match_rounds[-1],
        losers_round_matches=losers_bracket_rounds[-1],
        offset=running_match_count,
    )
    losers_bracket_rounds.append(losers_bracket_last_round)
    running_match_count += len(losers_bracket_last_round)

    # now the winners vs losers match
    bracket_joining_match = Match(
        source_match_a=match_rounds[-1][0],
        source_match_b=losers_bracket_last_round[0],
        team_a=None,
        team_b=None,
        number=running_match_count + 1,
    )
    match_rounds.append([bracket_joining_match])
    running_match_count += 1
    # and the "if-necessary" match
    if_necessary_match = Match(
        source_match_a=bracket_joining_match,
        source_match_b=bracket_joining_match,
        team_a=None,
        team_b=None,
        number=running_match_count + 1,
        a_want_winner=False,
    )
    match_rounds.append([if_necessary_match])

# now set the play order ...
all_matches = []
# first the first round from each of the brackets
play_order_inc = 1
for match in match_rounds[0] + (losers_bracket_rounds[0] if len(losers_bracket_rounds) else []):
    match.play_order = play_order_inc
    all_matches.append(match)
    play_order_inc += 1

round_inc = 1
while round_inc < round_count:
    print("working on round {}".format(round_inc))
    for match in match_rounds[round_inc]:
        match.play_order = play_order_inc
        print("set order for match {} to {}".format(match.number, match.play_order))
        all_matches.append(match)
        play_order_inc += 1
    for losers_bracket_match in \
            losers_bracket_rounds[2 * round_inc - 1] + \
            losers_bracket_rounds[2 * round_inc] if len(losers_bracket_rounds) > 2 * round_inc else []:
        losers_bracket_match.play_order = play_order_inc
        all_matches.append(losers_bracket_match)
        play_order_inc += 1
    round_inc += 1

# now add and order the matches that are on the winners and losers side, but aren't in the order in the predictable way
# print("the rounds expected not to be ordered are: %s" % [match_rounds[round_count:] + losers_bracket_rounds[-1]])
if args.type == 'double':
    for match in losers_bracket_rounds[-1] + match_rounds[round_count] + match_rounds[-1]:
        match.play_order = play_order_inc
        all_matches.append(match)
        play_order_inc += 1

# print("match rounds: %s losers rounds: %s" % (len(match_rounds), len(losers_bracket_rounds)))

# i = 0
# for match_round in match_rounds:
#     print("winners round %d" % (i + 1))
#     for match in match_round:
#         # print(" %s: %s" % (match, match.play_order or match.number))
#         print(" %s: %s" % (match, match.play_order))
#         # print(match)
#     i += 1
#
# # print("there are {} losers bracket rounds".format(len(losers_bracket_rounds)))
# i = 0
# for losers_bracket_round in losers_bracket_rounds:
#     print("losers round %d" % (i + 1))
#     for match in losers_bracket_round:
#         # print(" %s: %s" % (match, match.play_order or match.number))
#         print(" %s: %s" % (match, match.play_order))
#         # print(match)
#     i += 1
#

for match in all_matches:
    print("{} has number {} and order {}".format(match, match.number, match.play_order))
