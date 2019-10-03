from django.db import models
from django.urls import reverse
from math import ceil, log
from copy import deepcopy


TOURNAMENT_TYPES = [
    ('team_playoff', 'Team Playoff'),
    ('scotch_doubles', 'Scotch Doubles'),
]

ELIMINATION_TYPES = [
    ('single', 'Single Elimination'),
    ('double', 'Double Elimination'),
]

BRACKET_TYPES = [
    ('w', 'Winners'),
    ('l', 'Losers'),
]

BRACKET_TYPES_DICT = {
    x[0]: x[1] for x in BRACKET_TYPES
}

ROUND_TYPES = [
    'elimination',
    'drop_in',
]

# these do/must match the field names in Participant, below
PARTICIPANT_TYPES = [
    ('team', 'Team'),
    ('player', 'Player'),
]

PARTICIPANT_LETTERS = ['a', 'b']


class Tournament(models.Model):
    name = models.TextField()
    type = models.TextField(choices=TOURNAMENT_TYPES)
    elimination = models.TextField(choices=ELIMINATION_TYPES)
    season = models.ForeignKey('Season', on_delete=models.CASCADE, null=True)

    def __str__(self):
        return self.name

    def create_brackets(self):
        winners_bracket, created = Bracket.objects.get_or_create(tournament=self, type='w')
        winners_bracket.save()
        if self.elimination == 'double':
            losers_bracket, created = Bracket.objects.get_or_create(tournament=self, type='l')
            losers_bracket.save()

    def round_count(self):
        return ceil(log(len(self.participant_set.all()), 2))

    def bracket_size(self):
        return 2 ** self.round_count()

    def create_rounds(self):
        round_inc = 0
        winners_bracket_round_count = self.round_count()
        if self.elimination == 'double':
            # add 2 more winners's bracket rounds, for the match between the 2 bracket
            # winners, and the "if-necessary" match for case where the winner's bracket
            # winner loses the first match.
            winners_bracket_round_count += 2

            losers_bracket_round_inc = 0
            losers_bracket_round_count = 2 * (self.round_count() - 1)
            while losers_bracket_round_inc < losers_bracket_round_count:
                lbr, created = Round.objects.get_or_create(
                    bracket=self.bracket_set.get(type='l'),
                    number=losers_bracket_round_inc + 1,
                )
                lbr.save()
                losers_bracket_round_inc += 1
        while round_inc < winners_bracket_round_count:
            wbr, created = Round.objects.get_or_create(
                bracket=self.bracket_set.get(type='w'),
                number=round_inc + 1,
            )
            wbr.save()
            round_inc += 1


class Participant(models.Model):
    type = models.TextField(choices=PARTICIPANT_TYPES)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    # these field names do/must match the PARTICIPANT_TYPES list above;
    # for scotch-doubles tournaments, we'll add 2 players
    player = models.ManyToManyField('Player', blank=True)
    team = models.ForeignKey('Team', on_delete=models.DO_NOTHING, null=True, blank=True)

    def __str__(self):
        if self.type == 'player':
            return ', '.join([p.__str__() for p in self.player.all()])
        return getattr(self, '{}'.format(self.type)).__str__()

    def to_dict(self):
        players = []
        team = None
        if self.type == 'player':
            players = [{
                'id': p.id,
                'name': p.__str__(),
                'url': reverse('player', kwargs={'player_id': p.id})

            } for p in self.player.all()]
        else:
            team = [self.team.id]
        return {
            'id': self.id,
            'type': self.type,
            'players': players,
            'team': team,
        }


class Bracket(models.Model):
    type = models.TextField(choices=BRACKET_TYPES)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)

    def __str__(self):
        return '{} - {}'.format(self.tournament, BRACKET_TYPES_DICT[self.type])


class Round(models.Model):
    bracket = models.ForeignKey(Bracket, on_delete=models.CASCADE)
    number = models.IntegerField(null=True)

    default_matchup_args = {
        'source_match_a': None,
        'source_match_b': None,
        # participants; only set in first round winner's side
        'participant_a': None,
        'participant_b': None,
        # do we want winners? mostly yes; override for drop-in matches
        'a_want_winner': True,
        'b_want_winner': True,
    }

    def __str__(self):
        return '{}-{}'.format(self.bracket.type, self.number)

    def matchup_count(self):
        if self.bracket.type is 'w':
            return int(self.bracket.tournament.bracket_size() / 2 ** self.number)
        else:
            # LS round sizes from bracket of 64: 16, 16, 8, 8, 4, 4, 2, 2, 1
            # if round number is not divisible by 2, add 1, then use that as the power of 2 for the divisor
            return int(self.bracket.tournament.bracket_size() / 2 ** ((self.number + (self.number % 2)) / 2 + 1))

    def get_first_round_winners_participant(self, ab, increment):
        if ab == 'a':
            return self.bracket.tournament.participant_set.all()[increment]
        if len(self.bracket.tournament.participant_set.all()) > (2 * self.matchup_count() - 1) - increment:
            return self.bracket.tournament.participant_set.all()[(2 * self.matchup_count()  - 1) - increment]
        return None

    def get_first_round_losers_source_matchup(self, ab, increment):
        source_round_matchups = self.bracket.tournament.bracket_set.get(type='w').round_set.get(number=1).tournamentmatchup_set.all()
        if ab == 'a':
            return source_round_matchups[increment]
        else:
            return source_round_matchups[self.matchup_count() * 2 - increment -1]

    def get_winners_bracket_source_matchup(self, ab, increment):
        source_matchups = self.bracket.tournament.bracket_set.get(type='w').round_set.get(number=self.number - 1).tournamentmatchup_set.all()
        if ab == 'a':
            return source_matchups[increment]
        else:
            return source_matchups[2 * self.matchup_count() - increment - 1]

    def get_losers_bracket_elimination_source_matchups(self, ab, increment):
        source_round_matchups = self.bracket.tournament.bracket_set.get(type='l').round_set.get(number=self.number - 1).tournamentmatchup_set.all()
        if ab == 'a':
            return source_round_matchups[increment]
        else:
            return source_round_matchups[self.matchup_count() - increment - 1]  # yikes why does this work

    def get_losers_bracket_drop_in_source_matchup(self, ab, increment):
        winners_source_round_number = int(self.number / 2) + 1
        winners_source_matches = self.bracket.tournament.bracket_set.get(type='w').round_set.get(number=winners_source_round_number).tournamentmatchup_set.all()
        losers_source_matches = self.bracket.tournament.bracket_set.get(type='l').round_set.get(number=self.number - 1).tournamentmatchup_set.all()
        if ab == 'a':
            return winners_source_matches[increment]
        else:
            return losers_source_matches[increment]

    def create_matchups(self):

        # first round winners side match-ups; assumes participant_set is in the desired order
        i = 0
        matchup_count = self.matchup_count()
        while i < matchup_count:
            matchup_args = deepcopy(self.default_matchup_args)
            matchup_args['round'] = self
            matchup_args['number'] = i + 1
            if self.number == 1:
                if self.bracket.type is 'w':
                    for p in PARTICIPANT_LETTERS:
                        matchup_args['participant_{}'.format(p)] = self.get_first_round_winners_participant(p, i)
                else:
                    # losers bracket round one is also a special case; we initialize from losers of all the
                    # round one winners side matches
                    for p in PARTICIPANT_LETTERS:
                        matchup_args['source_match_{}'.format(p)] = self.get_first_round_losers_source_matchup(p, i)
                        matchup_args['{}_want_winner'.format(p)] = False

            else:
                if self.bracket.type is 'w':
                    for p in PARTICIPANT_LETTERS:
                        matchup_args['source_match_{}'.format(p)] = self.get_winners_bracket_source_matchup(p, i)
                elif self.number % 2 == 0:
                    # this is a "drop-in" losers bracket round; we mix the losers bracket winners and winners bracket losers
                    matchup_args['a_want_winner'] = False
                    matchup_args['source_match_a'] = self.get_losers_bracket_drop_in_source_matchup('a', i)
                    matchup_args['source_match_b'] = self.get_losers_bracket_drop_in_source_matchup('b', i)
                else:
                    # this is an "elimination" losers bracket round; source matches are the previous round
                    for p in PARTICIPANT_LETTERS:
                        matchup_args['source_match_{}'.format(p)] = self.get_losers_bracket_elimination_source_matchups(p, i)

            tm, created = TournamentMatchup.objects.get_or_create(
                **matchup_args,
            )
            print("matchup {} vs {}:  was created: {}".format(
                tm.participant_a, tm.participant_b, created)
            )
            tm.save()
            i += 1

    def create_finals_matchup(self, step):

        matchup_args = deepcopy(self.default_matchup_args)
        matchup_args['round'] = self
        matchup_args['number'] = 1

        # the participants are the same either way, for the last 2 matches, just the round that needs over-ridden in
        # the second case
        winners_side_source_round_number = self.number - 1

        # first need the number of rounds in the losers side
        losers_side_round_count = 2 * (self.bracket.tournament.round_count() - 1)

        losers_side_source_round = self.bracket.tournament.bracket_set.get(type='l').round_set.get(number=losers_side_round_count)
        if step == 'second':
            winners_side_source_round_number = self.number - 2
        source_matchup_a = self.bracket.tournament.bracket_set.get(type='w').round_set.get(
            number=winners_side_source_round_number).tournamentmatchup_set.all()[0] # there should be exactly one right
        source_matchup_b = losers_side_source_round.tournamentmatchup_set.all()[0]

        matchup_args['source_match_a'] = source_matchup_a
        matchup_args['source_match_b'] = source_matchup_b
        tm, created = TournamentMatchup.objects.get_or_create(
            **matchup_args,
        )
        print("matchup {} vs {}:  was created: {}".format(
            tm.participant_a, tm.participant_b, created)
        )


class TournamentMatchup(models.Model):

    round = models.ForeignKey(Round, on_delete=models.DO_NOTHING)
    # TODO: make deleting a round delete a matchup
    source_match_a = models.ForeignKey(
        'TournamentMatchup', on_delete=models.DO_NOTHING, null=True,
        related_name='match_a',
    )
    source_match_b = models.ForeignKey(
        'TournamentMatchup', on_delete=models.DO_NOTHING, null=True,
        related_name='match_b',
    )

    participant_a = models.ForeignKey(
        Participant, on_delete=models.DO_NOTHING, null=True,
        related_name='participant_a'
    )
    participant_b = models.ForeignKey(
        Participant, on_delete=models.DO_NOTHING, null=True,
        related_name='participant_b'
    )

    winner = models.ForeignKey(
        Participant, on_delete=models.DO_NOTHING, null=True,
    )

    def not_winner(self):
        for p in [self.participant_a, self.participant_b]:
            if p != self.winner:
                return p

    number = models.IntegerField()
    a_want_winner = models.NullBooleanField(null=True)
    b_want_winner = models.NullBooleanField(null=True)
    play_order = models.IntegerField(null=True)

    def update(self):
        if self.source_match_a.winner:
            print("source match a {} has a winner: {}".format(self.source_match_a, self.source_match_a.winner))
            if self.a_want_winner:
                self.participant_a = self.source_match_a.winner
            else:
                self.participant_a = self.source_match_a.not_winner()
        if self.source_match_b.winner:
            print("source match b {} has a winner: {}".format(self.source_match_b, self.source_match_b.winner))
            if self.b_want_winner:
                self.participant_b = self.source_match_b.winner
            else:
                self.participant_b = self.source_match_b.not_winner()
        self.save()

    # def description(self, side, want):
    #     # print('describing match {}'.format(self.number))
    #     if self.winner:
    #         return self.participant_a if self.winner == self.participant_a else self.participant_b
    #     else:
    #         return "winner of "
        # else:
        #     if self.participant_a and self.participant_b:
        #         description = "{} of {} vs {}".format("winner" if want else "loser", self.participant_a, self.participant_b)
        #     else:
        #         description = "{}".format(self.participant_a or self.participant_b)
        #
        #     src_m = getattr(self, 'source_match_{}'.format(side), None)
        #     if src_m is not None:
        #         description = "{} of match {}".format("winner" if want else "loser", self.play_order)
        #     return description

    def __str__(self):
        return "match in {} of {}".format(self.round, self.round.bracket)
        # print('stringing match number {} in bracket {}/{} tournament {} between {} and {}'.format(
        #     self.play_order, self.round.bracket, self.round.bracket.type, self.round.bracket.tournament,
        #     self.participant_a, self.participant_b,
        # ))
        #
        # participant_b_string = self.participant_b
        # if self.participant_b is None:
        #     if self.source_match_b is not None:
        #         participant_b_string = self.source_match_b.description('b', self.b_want_winner)
        #     else:
        #         participant_b_string = 'bye'
        #
        # return ("match {}: {} vs {}".format(
        #     self.play_order,
        #     'bye' if self.participant_a is False else self.participant_a or
        #         self.source_match_a.description('a', self.a_want_winner),
        #         participant_b_string
        #     )
        # )
