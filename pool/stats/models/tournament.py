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

PARTICIPANT_TYPES = [
    ('team', 'Team'),
    ('player', 'Player'),
    ('scotch', 'Scotch Doubles Team'),
]


class Tournament(models.Model):
    name = models.TextField()
    type = models.TextField(choices=TOURNAMENT_TYPES)
    elimination = models.TextField(choices=ELIMINATION_TYPES)

    # class Meta:
    #     abstract = True


class TeamPlayoffTournament(Tournament):
    pass


class Bracket(models.Model):
    type = models.TextField(choices=BRACKET_TYPES)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)


class Round(models.Model):
    bracket = models.ForeignKey(Bracket, on_delete=models.CASCADE)
    number = models.IntegerField(null=True)

    def __str__(self):
        return '{}-{}'.format(self.bracket.type, self.number)


class TeamPlayoffMatchup(models.Model):

    round = models.ForeignKey(Round, on_delete=models.DO_NOTHING)
    source_match_a = models.ForeignKey(
        'TeamPlayoffMatchup', on_delete=models.DO_NOTHING, null=True,
        related_name='match_a',
    )
    source_match_b = models.ForeignKey(
        'TeamPlayoffMatchup', on_delete=models.DO_NOTHING, null=True,
        related_name='match_b',
    )

    team_a = models.ForeignKey(
        'Team', on_delete=models.DO_NOTHING, null=True,
        related_name='team_a'
    )
    team_b = models.ForeignKey(
        'Team', on_delete=models.DO_NOTHING, null=True,
        related_name='team_b'
    )

    winner = models.ForeignKey(
        'Team', on_delete=models.DO_NOTHING, null=True,
    )

    number = models.IntegerField()
    a_want_winner = models.BooleanField()
    b_want_winner = models.BooleanField()
    play_order = models.IntegerField()

    def teams_desc(self, side, want):
        if self.team_a and self.team_b:
            description = "{} of {} vs {}".format("winner" if want else "loser", self.team_a, self.team_b)
        else:
            description = "{}".format(self.team_a or self.team_b)

        src_m = getattr(self, 'source_match_{}'.format(side), None)
        if src_m is not None:
            description = "{} of match {}".format("winner" if want else "loser", self.play_order)
        return description

    def __str__(self):

        return ("match {}: {} vs {}".format(
            self.play_order,
            'bye' if self.team_a is False else self.team_a or self.source_match_a.teams_desc('a',
                                                                                             self.a_want_winner),
            'bye' if self.team_b is False else self.team_b or self.source_match_b.teams_desc('b',
                                                                                             self.b_want_winner),
        ))


class Participant(models.Model):
    type = models.TextField(choices=PARTICIPANT_TYPES)
    team = models.ForeignKey('Team', on_delete=models.DO_NOTHING, null=True, blank=True)
    player = models.ForeignKey(
        'Player',
        related_name='tournament_player',
        on_delete=models.DO_NOTHING, null=True, blank=True)
    scotch_team = models.ManyToManyField(
        'Player',
        related_name='scotch_team_member',
    )
