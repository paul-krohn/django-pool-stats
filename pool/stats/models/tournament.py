from django.db import models
from math import ceil, log


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

ROUND_TYPES = [
    'elimination',
    'drop_in',
]

# these do/must match the field names in Participant, below
PARTICIPANT_TYPES = [
    ('team', 'Team'),
    ('player', 'Player'),
    ('scotch', 'Scotch Doubles Team'),
]


class Tournament(models.Model):
    name = models.TextField()
    type = models.TextField(choices=TOURNAMENT_TYPES)
    elimination = models.TextField(choices=ELIMINATION_TYPES)
    season = models.ForeignKey('Season', on_delete=models.CASCADE, null=True)

    def __str__(self):
        return self.name

    def create_brackets(self):
        winners_bracket = Bracket(tournament=self, type='w')
        winners_bracket.save()
        if self.elimination is 'double':
            losers_bracket = Bracket(tournament=self, type='l')
            losers_bracket.save()

    def round_count(self):
        return ceil(log(len(self.participant_set.all()), 2))

    def bracket_size(self):
        return 2 ** self.round_count()

    def create_rounds(self):
        round_inc = 0
        while round_inc < self.round_count():
            wbr = Round(
                bracket=self.bracket_set.get(type='w'),
                number=round_inc + 1,
            )
            wbr.save()
            round_inc += 1
        if self.elimination == 'double':
            losers_bracket_round_inc = 0
            losers_bracket_round_count = 2 * (self.round_count() - 1)
            while losers_bracket_round_inc < losers_bracket_round_count:
                lbr, created = Round.objects.get_or_create(
                    bracket=self.bracket_set.get(type='l'),
                    number=losers_bracket_round_inc + 1,
                )
                lbr.save()
                losers_bracket_round_inc += 1



class Participant(models.Model):
    type = models.TextField(choices=PARTICIPANT_TYPES)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    # these field names do/must match the PARTICIPANT_TYPES list above
    player = models.ForeignKey('Player', on_delete=models.DO_NOTHING, null=True)
    team = models.ForeignKey('Team', on_delete=models.DO_NOTHING, null=True)
    scotch = models.ForeignKey('ScotchDoublesTeam', on_delete=models.DO_NOTHING, null=True)

    def __str__(self):
        return getattr(self, '{}'.format(self.type)).__str__()


class Bracket(models.Model):
    type = models.TextField(choices=BRACKET_TYPES)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)


class Round(models.Model):
    bracket = models.ForeignKey(Bracket, on_delete=models.CASCADE)
    number = models.IntegerField(null=True)

    def __str__(self):
        return '{}-{}'.format(self.bracket.type, self.number)


    def matchup_count(self):
        if self.bracket.type is 'w':
            # return log(foo, 2) - (self.number - 1)
            return int(self.bracket.tournament.bracket_size() / 2 ** self.number)
        else:
            # LS round sizes from bracket of 64: 16, 16, 8, 8, 4, 4, 2, 2, 1
            # if round number is not divisible by 2, add 1, then use that as the power of 2 for the divisor
            return int(self.bracket.tournament.bracket_size() / (2 ** (self.number + ceil(self.number % 2))))

    def create_matchups(self):

        # first round winners side matchups; assumes participant_set is in the desired order
        i = 0
        matchup_count = self.matchup_count()
        br_size = 2 * matchup_count

        winners_side_rounds = self.bracket.tournament.bracket_set.get(type='w').round_set.all()
        losers_side_rounds = self.bracket.tournament.bracket_set.get(type='l').round_set.all()

        while i < matchup_count:
            # source matches; not set in first round
            sma = None
            smb = None
            # participants; only set in first round winner's side
            pa = None
            pb = None
            if self.number == 1:
                if self.bracket.type is 'w':
                    pa = self.bracket.tournament.participant_set.all()[i]
                    pb = None  # allows for byes when the bracket is not full
                    if len(self.bracket.tournament.participant_set.all()) > (br_size - 1) - i:
                        pb = self.bracket.tournament.participant_set.all()[(br_size - 1) - i]
                else:
                    # losers bracket round one is also a special case; we initialize from losers of all the
                    # round one winners side matches
                    # source_round = self.bracket.tournament.bracket_set.get(type__eq='w').round_set.get(number=1)
                    source_round_matchups = winners_side_rounds.get(number=1).tournamentmatchup_set.all()
                    sma = source_round_matchups[i]
                    smb = source_round_matchups[br_size - i - 1]
            else:
                if self.bracket.type is 'w':
                    source_round_matchups = winners_side_rounds.get(number=self.number - 1).tournamentmatchup_set.all()
                    sma = source_round_matchups[i]
                    smb = source_round_matchups[br_size - i - 1]
                elif self.number % 2 == 0:
                    # this is an "elimination" losers bracket round; source matches are the previous round
                    source_round_matchups = losers_side_rounds.get(number=self.number - 1).tournamentmatchup_set.all()
                    print("source round matchups: {}".format(source_round_matchups))
                    sma = source_round_matchups[i]
                    smb = source_round_matchups[matchup_count - i - 1]  # yikes why does this work
                else:
                    # this is a "drop-in" losers bracket round; we mix the losers and winners brackets
                    winners_source_matches = winners_side_rounds.get(number=self.number - 1).tournamentmatchup_set.all()
                    losers_source_matches = losers_side_rounds.get(number=self.number - 1).tournamentmatchup_set.all()
                    sma = winners_source_matches[i]
                    smb = losers_source_matches[i]

            tm, created = TournamentMatchup.objects.get_or_create(
                source_match_a=sma,
                source_match_b=smb,
                participant_a=pa,
                participant_b=pb,
                # round=self.bracket_set.get(type=side).round_set.get(number=1),
                round=self,
                number=i + 1,
            )
            print("matchup {} vs {}:  was created: {}".format(
                tm.participant_a, tm.participant_b, created)
            )
            tm.save()
            i += 1


class TournamentMatchup(models.Model):

    round = models.ForeignKey(Round, on_delete=models.DO_NOTHING)
    source_match_a = models.ForeignKey(
        'stats.TournamentMatchup', on_delete=models.DO_NOTHING, null=True,
        related_name='match_a',
    )
    source_match_b = models.ForeignKey(
        'stats.TournamentMatchup', on_delete=models.DO_NOTHING, null=True,
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

    def description(self, side, want):
        if self.participant_a and self.participant_b:
            description = "{} of {} vs {}".format("winner" if want else "loser", self.participant_a, self.participant_b)
        else:
            description = "{}".format(self.participant_a or self.participant_b)

        src_m = getattr(self, 'source_match_{}'.format(side), None)
        if src_m is not None:
            description = "{} of match {}".format("winner" if want else "loser", self.play_order)
        return description

    def __str__(self):

        return ("match {}: {} vs {}".format(
            self.play_order,
            'bye' if self.participant_a is False else self.participant_a or
                self.source_match_a.description('a', self.a_want_winner),
            'bye' if self.participant_b is False else self.participant_b or
                self.source_match_b.description('b', self.b_want_winner),
                )
        )

