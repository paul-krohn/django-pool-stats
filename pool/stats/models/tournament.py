from django.db import models
from django.urls import reverse
from math import ceil, log
from statistics import mean
from copy import deepcopy
from random import choice

from ..models import PlayerSeasonSummary
from ..utils import is_stats_master, session_uid


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
    ('doubles_players', 'Player'),
]

PARTICIPANT_LETTERS = ['a', 'b']


class Tournament(models.Model):
    name = models.TextField()
    creator_session = models.CharField(max_length=16, null=True, blank=True)
    type = models.TextField(choices=TOURNAMENT_TYPES)
    elimination = models.TextField(choices=ELIMINATION_TYPES)
    season = models.ForeignKey('Season', on_delete=models.CASCADE, null=True)
    seeded = models.BooleanField(default=False)
    flopped = models.BooleanField(default=False)
    third_place = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def as_dict(self, request):
        response_dict = dict(
            id=self.id,
            editable=self.editable(request),
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
                    matchup_field_names = [
                        'id', 'number', 'a_want_winner', 'b_want_winner', 'is_necessary'
                    ]
                    this_matchup = {f:getattr(matchup, str(f)) for f in matchup_field_names}
                    this_matchup['bye_winner'] = matchup.bye_winner()
                    this_matchup['parent'] = matchup.parent_id()
                    this_matchup['name'] = matchup.code_name()
                    this_matchup['source_match_a'] = None if not matchup.source_match_a else matchup.source_match_a.id
                    this_matchup['source_match_b'] = None if not matchup.source_match_b else matchup.source_match_b.id
                    this_matchup['participant_a'] = None if not matchup.participant_a else matchup.participant_a.to_dict()
                    this_matchup['participant_b'] = None if not matchup.participant_b else matchup.participant_b.to_dict()
                    this_matchup['winner'] = None if not matchup.winner else matchup.winner.to_dict()

                    this_round['matchups'].append(this_matchup)
                this_bracket_round_list.append(this_round)
            response_dict['brackets'].append({
                'type': bracket.type, 'rounds': this_bracket_round_list
            })
        return response_dict

    def editable(self, request):
        return self.creator_session == session_uid(request) or \
                request.user.is_superuser or is_stats_master(request.user)

    def create_brackets(self):
        winners_bracket, created = Bracket.objects.get_or_create(tournament=self, type='w')
        winners_bracket.save()
        if self.elimination == 'double':
            losers_bracket, created = Bracket.objects.get_or_create(tournament=self, type='l')
            losers_bracket.save()

    def round_count(self):
        participant_count = len(self.participant_set.all())
        if participant_count > 0:
            return ceil(log(participant_count, 2))
        else:
            return 0

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

    def update_places(self):
        bracket_size = self.bracket_size()
        for p in self.participant_set.all():
            p.place = None
            p.save()
        offset = 0
        count = 0
        bracket = 'w'
        if self.elimination == 'double':
            # determine most of the placings with the losers' bracket results
            offset = 3  # the winner of the 2 brackets will get 1, 2
            count = 0
            bracket = 'l'
        for _round in self.bracket_set.get(type=bracket).round_set.all().order_by('-number'):
            # if you lost in the first losers bracket round, you tied for the bottom 1/4 of the bracket
            # your place is bracket_size / 2 + bracket_size / 4
            matchups = _round.tournamentmatchup_set.all()
            number_of_participants_with_this_place = len(matchups)
            for matchup in matchups:
                loser = matchup.not_winner()
                if loser:
                    loser.place = offset + count
                    loser.save()
            count += number_of_participants_with_this_place
        if self.elimination == 'double':
            # now get the 1-2 from the winners bracket
            rounds = self.bracket_set.get(type='w').round_set.filter(number__gt=self.round_count()).order_by('number')
            print('the rounds are: {}'.format(rounds))
            # if the last-round matchup "is_necessary" then we need the winner of that, else the winner of the previous round
            top_two_participants = [None, None]
            last_round_matchup = rounds[1].tournamentmatchup_set.all()[0]
            if last_round_matchup.is_necessary and last_round_matchup.winner:
                top_two_participants[0] = last_round_matchup.winner
                top_two_participants[1] = last_round_matchup.not_winner()
            else:
                matchup = rounds[0].tournamentmatchup_set.all()[0]
                top_two_participants[0] = matchup.winner
                top_two_participants[1] = matchup.not_winner()

            i = 1
            for participant in top_two_participants:
                participant.place = i
                participant.save()
                i += 1

    def create_third_place_matchup(self):

        source_round = self.bracket_set.get(type='w').round_set.get(number=self.round_count() - 1)
        source_matchups = source_round.tournamentmatchup_set.all()

        m, created = TournamentMatchup.objects.get_or_create(
            round=self.bracket_set.get(type='w').round_set.get(number=self.round_count()),
            number=2,
            source_match_a=source_matchups[0],
            source_match_b=source_matchups[1],
            a_want_winner=False,
            b_want_winner=False,
        )


class Participant(models.Model):
    type = models.TextField(choices=PARTICIPANT_TYPES)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    # these field names do/must match the PARTICIPANT_TYPES list above;
    # for scotch-doubles tournaments,
    doubles_players = models.ManyToManyField('Player', related_name='doubles_players', blank=True)
    player = models.ForeignKey('Player', on_delete=models.DO_NOTHING, null=True, blank=True)
    team = models.ForeignKey('Team', on_delete=models.DO_NOTHING, null=True, blank=True)
    seed = models.IntegerField(null=True, blank=True)

    def __str__(self):
        if self.type == 'doubles_players':
            return ', '.join([p.__str__() for p in self.doubles_players.all()])
        return getattr(self, '{}'.format(self.type)).__str__()

    def get_player_win_pct(self):

        player_summary_filter_args = {
            'season': self.tournament.season,
        }

        if self.type == 'player':
            player_summary_filter_args['player'] = self.player
        elif self.type == 'doubles_players':
            player_summary_filter_args['player__in'] = [x for x in self.doubles_players.all()]

        player_season_summaries = PlayerSeasonSummary.objects.filter(
            **player_summary_filter_args
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
        if self.type == 'team':
            team = {
                'id': self.team.id,
                'name': self.team.name,
                'url': reverse('team', kwargs={'team_id': self.team.id}),
            }
        else:
            if self.type == 'scotch_doubles':
                player_list = self.doubles_players.all()
            else:
                player_list = [self.player]
            players = [{
                'id': p.id,
                'name': p.__str__(),
                'url': reverse('player', kwargs={'player_id': p.id})

            } for p in player_list]

        return {'id': self.id,
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

    # These hard-coded orders could conceivably be replaced with an algorithm, but I don't know what it is;
    # in any case, the idea is to make it so the top seeds meet as late as possible.
    first_round_orders = {
        '4': [0, 2, 1, 3],
        '8': [0, 7, 3, 4, 1, 6, 2, 5],
        '16': [0, 15, 7, 8, 3, 12, 4, 11, 1, 14, 6, 9, 2, 13, 5, 10],
    }
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

        re_order =  self.first_round_orders[str(self.matchup_count())]

        participant_set = self.bracket.tournament.participant_set.all().order_by('seed')
        if ab == 'a':
            return participant_set[re_order[increment]]
        if len(participant_set) > (2 * self.matchup_count() - 1) - re_order[increment]:
            return participant_set[(2 * self.matchup_count()  - 1) - re_order[increment]]
        return None

    def get_first_round_losers_source_matchup(self, ab, increment):
        source_matchup_number = 2 * increment + 1
        if ab == 'b':
            source_matchup_number = 2 * increment + 2
        return self.bracket.tournament.bracket_set.get(type='w').round_set.get(number=1).tournamentmatchup_set.get(
            number=source_matchup_number,
        )

    def get_winners_bracket_source_matchup(self, ab, increment):
        if ab == 'a':
            source_match_number = 2 * increment + 1
        else:
            source_match_number = 2 * increment + 2
        return  self.bracket.tournament.bracket_set.get(type='w').round_set.get(number=self.number - 1).tournamentmatchup_set.get(
            number = source_match_number
        )

    def get_losers_bracket_elimination_source_matchups(self, ab, increment):
        source_matchup_number = 2 * increment + 1
        if ab == 'b':
            source_matchup_number = 2 * increment + 2
        return self.bracket.tournament.bracket_set.get(
            type='l').round_set.get(number=self.number - 1).tournamentmatchup_set.get(number=source_matchup_number)

    def get_losers_bracket_drop_in_source_matchup(self, ab, increment):

        # flop on alternating/even drop-in rounds
        # flop means the source from the winners side should be reverse order on even drop-in rounds`x

        source_match_number = increment + 1
        if ab == 'a':
            source_round_number = int(self.number / 2) + 1
            bracket = 'w'
        else:
            source_round_number = self.number - 1
            if self.number == 2 and self.bracket.tournament.flopped:
                source_match_number = self.matchup_count() - increment
            bracket = 'l'
        return self.bracket.tournament.bracket_set.get(type=bracket).round_set.get(
                number=source_round_number).tournamentmatchup_set.get(
                number=source_match_number
            )

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
                    matchup_args['source_match_a'] = self.get_losers_bracket_drop_in_source_matchup('a', matchup_count - 1 - i)
                    matchup_args['source_match_b'] = self.get_losers_bracket_drop_in_source_matchup('b', matchup_count - 1 - i)
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
        source_matchup_a = self.bracket.tournament.bracket_set.get(type='w').round_set.get(
            number=winners_side_source_round_number).tournamentmatchup_set.all()[0] # there should be exactly one right
        source_matchup_b = losers_side_source_round.tournamentmatchup_set.all()[0]
        if step == 'second':
            # this is the maybe-necessary last round/matchup
            matchup_args['is_necessary'] = False
            matchup_args['a_want_winner'] = False
            source_matchup_b = self.bracket.tournament.bracket_set.get(type='w').round_set.get(
                number=winners_side_source_round_number).tournamentmatchup_set.all()[0]

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
    number = models.IntegerField()
    a_want_winner = models.NullBooleanField(null=True)
    b_want_winner = models.NullBooleanField(null=True)
    play_order = models.IntegerField(null=True)
    is_necessary = models.BooleanField(default=True)

    def parent_id(self):
        parents = TournamentMatchup.objects.filter(
            models.Q(source_match_a__id=self.id) | models.Q(source_match_b__id=self.id)
        )
        return parents[0].id if len(parents) else None

    def not_winner(self):
        for p in [self.participant_a, self.participant_b]:
            if p != self.winner:
                return p

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
        if not self.is_necessary:
            # pass
            # if the winner of the 2ndlast winners bracket match is the winner of the loser's bracket,
            # then this match is now necessary
            hot_seat_matchup = self.source_match_a
            losers_bracket_final = self.source_match_a.source_match_b
            print("hot seat matchup id = {}".format(hot_seat_matchup.id))
            print("lb final matchup id = {}".format(losers_bracket_final.id))
            if hot_seat_matchup.winner_id == losers_bracket_final.winner_id:
                self.is_necessary = True
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

    def code_name(self):
        return "{}-{}-{}".format(self.round.bracket.type, self.round.number, self.number)
