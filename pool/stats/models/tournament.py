from django.db import models
from django.urls import reverse
from math import ceil, log
from statistics import mean
from copy import deepcopy
from random import choice

from ..models import PlayerSeasonSummary


TOURNAMENT_TYPES = [
    ('singles', 'Singles'),
    ('scotch_doubles', 'Scotch Doubles'),
    ('teams', 'Teams'),
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
    seeded = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def as_dict(self):
        response_dict = dict(
            id=self.id,
            name=self.name,
            type=self.type,
            elimination=self.elimination,
            season=self.season_id,
            participants=[participant.to_dict() for participant in self.participant_set.all().order_by('seed')],
        )

        # now the matchups
        response_dict.update(brackets=[])
        for bracket in self.bracket_set.all():
            this_bracket_round_list = []
            for round in bracket.round_set.all():
                this_round = {
                    'number': round.number,
                    'matchups': []
                }
                for matchup in round.tournamentmatchup_set.all():
                    this_round['matchups'].append({
                            'bye_winner': matchup.bye_winner(),
                            'name': matchup.__str__(),
                            'number': matchup.number,
                            'id': matchup.id,
                            'participant_a': None if not matchup.participant_a else matchup.participant_a.to_dict(),
                            'participant_b': None if not matchup.participant_b else matchup.participant_b.to_dict(),
                            'winner': None if not matchup.winner else matchup.winner.to_dict(),
                    })
                this_bracket_round_list.append(this_round)
            response_dict['brackets'].append({
                'type': bracket.type, 'rounds': this_bracket_round_list
            })
        return response_dict

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

    def update_seeds(self):
        participants = Participant.objects.filter(tournament=self)
        if self.type == 'teams':
            sorted_participants = participants.order_by('team__ranking')
        else:  # self.type in ['singles', 'scotch_doubles']:
            sorted_participants = sorted(participants)
        seed_inc = 1

        for participant in sorted_participants:
            participant.seed = seed_inc
            participant.save()
            seed_inc += 1

    def randomize_seeds(self):
        participants = Participant.objects.filter(tournament=self)
        available_seeds = [x+1 for x in range(0, len(participants))]
        # don't re-seed participants, I think
        for participant in participants:
            if participant.seed:
                available_seeds.remove(participant.seed)
        for participant in participants:
            if not participant.seed:
                this_seed = choice(available_seeds)
                participant.seed = this_seed
                participant.save()
                available_seeds.remove(this_seed)


class Participant(models.Model):
    type = models.TextField(choices=PARTICIPANT_TYPES)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    # these field names do/must match the PARTICIPANT_TYPES list above;
    # for scotch-doubles tournaments, we'll add 2 players
    player = models.ManyToManyField('Player', blank=True)
    team = models.ForeignKey('Team', on_delete=models.DO_NOTHING, null=True, blank=True)
    seed = models.IntegerField(null=True, blank=True)

    def __str__(self):
        if self.type == 'player':
            return ', '.join([p.__str__() for p in self.player.all()])
        return getattr(self, '{}'.format(self.type)).__str__()

    def get_player_win_pct(self):

        player_season_summaries = PlayerSeasonSummary.objects.filter(
            player__in=self.player.all(),
            season=self.tournament.season,
        )

        # for seeded tournaments, we rely on a filter in the form to only allow the
        # user to select players with a season summary, and at least one game played.
        return mean([
            p.win_percentage for p in player_season_summaries
        ])

    def __cmp__(self, other):
        if self.type == 'player':
            if self.tournament.type == 'singles':
                return self.get_player_win_pct().__cmp__(other.get_player_win_pct())

        elif self.type == 'team':
            return self.team.ranking.__cmp__(other.team.ranking())

    def __lt__(self, other):
        if self.type == 'player':
            print("looking at {} compared to {}".format(self, other))
            return self.get_player_win_pct() > other.get_player_win_pct()

        elif self.type == 'team':
            return self.team.ranking < other.team.ranking()

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
            team = {
                'id': self.team.id,
                'name': self.team.name,
                'url': reverse('team', kwargs={'team_id': self.team.id}),
            }
        return {
            'id': self.id,
            'players': players,
            'seed': self.seed,
            'team': team,
            'type': self.type,
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
        participant_set = self.bracket.tournament.participant_set.all().order_by('seed')
        if ab == 'a':
            return participant_set[increment]
        if len(participant_set) > (2 * self.matchup_count() - 1) - increment:
            return participant_set[(2 * self.matchup_count()  - 1) - increment]
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
            return source_round_matchups[2 * self.matchup_count() - increment - 1]

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

    def no_match(self):
        if self.a_want_winner is False and self.b_want_winner is False and self.source_match_a.bye_winner() and self.source_match_b.bye_winner():
            return True
        return False
    def bye_winner(self):
        if bool(self.participant_a is None) ^ bool(self.participant_b is None):
            # winners first round byes
            if self.round.number == 1 and self.round.bracket.type == 'w':
                if self.participant_a:
                    return self.participant_a.id
                elif self.participant_b:
                    return self.participant_b.id
            if self.round.number == 1 and self.round.bracket.type == 'l':
                if self.participant_a is not None and self.source_match_b.bye_winner():
                    return self.participant_a.id
                if self.participant_b is not None and self.source_match_a.bye_winner():
                    return self.participant_b.id
            if self.source_match_b.no_match():
                return self.participant_a.id
            if self.source_match_a.no_match():
                return self.participant_b.id
        return 0


    def __str__(self):
        return "{}-{}".format(self.round, self.number)
