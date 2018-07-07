from django.db import models


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
    a_want_winner = models.BooleanField()
    b_want_winner = models.BooleanField()
    play_order = models.IntegerField()

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

