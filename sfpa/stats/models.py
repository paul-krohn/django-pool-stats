from django.db import models


class Sponsor(models.Model):
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=200)
    link = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Season(models.Model):
    name = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date of first week')
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Player(models.Model):
    first_name = models.CharField(max_length=64)
    last_name = models.CharField(max_length=64)
    display_name = models.CharField(max_length=128, null=True, blank=True)

    def __str__(self):
        return self.display_name or "%s %s" % (self.first_name, self.last_name)


class Division(models.Model):
    season = models.ForeignKey(Season)
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name


class Team(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    sponsor = models.ForeignKey(Sponsor, null=True)
    division = models.ForeignKey(Division, null=True)
    name = models.CharField(max_length=200)
    players = models.ManyToManyField(Player, blank=True)

    def __str__(self):
        return "{}".format(self.name)


class Week(models.Model):
    season = models.ForeignKey(Season)
    date = models.DateField(null=True, blank=True)
    name = models.CharField(max_length=32, null=True)

    def __str__(self):
        return "Week {}".format(self.name)


class AwayTeam(Team):
    class Meta:
        proxy = True


class HomeTeam(Team):
    class Meta:
        proxy = True


class Match(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    week = models.ForeignKey(Week)
    home_team = models.ForeignKey(HomeTeam)
    away_team = models.ForeignKey(AwayTeam)

    def __str__(self):
        # return "{} @ {}".format(self.away_team, self.home_team)
        return "{} @ {} ({} {})".format(self.away_team, self.home_team, self.season, self.week)


class PlayPosition(models.Model):
    home_name = models.CharField(max_length=16)
    away_name = models.CharField(max_length=16)
    name = models.CharField(max_length=16)

    def __str__(self):
        return self.name


class AwayPlayPosition(PlayPosition):
    class Meta:
        proxy = True

    def __str__(self):
        return self.away_name


class HomePlayPosition(PlayPosition):
    class Meta:
        proxy = True

    def __str__(self):
        return self.home_name


class AwayPlayer(Player):
    class Meta:
        proxy = True


class HomePlayer(Player):
    class Meta:
        proxy = True


class GameOrder(models.Model):

    away_position = models.ForeignKey(AwayPlayPosition)
    home_position = models.ForeignKey(HomePlayPosition)
    name = models.CharField(max_length=8)

    def __str__(self):
        return "{} ({} vs {})".format(self.name, self.away_position, self.home_position)


class Game(models.Model):
    away_player = models.ForeignKey(AwayPlayer, null=True, blank=True)
    home_player = models.ForeignKey(HomePlayer, null=True, blank=True)
    winner = models.CharField(max_length=4, blank=True)
    order = models.ForeignKey(GameOrder, null=True)
    table_run = models.BooleanField()
    forfeit = models.BooleanField()


class LineupEntry(models.Model):
    player = models.ForeignKey(Player, null=True)
    position = models.ForeignKey(PlayPosition, null=True)


class AwayLineupEntry(LineupEntry):
    class Meta:
        proxy = True


class HomeLineupEntry(LineupEntry):
    class Meta:
        proxy = True


class Substitution(models.Model):
    game_order = models.ForeignKey(GameOrder)
    player = models.ForeignKey(Player, null=True, blank=True)
    play_position = models.ForeignKey(PlayPosition)


class AwaySubstitution(Substitution):
    class Meta:
        proxy = True

    def __str__(self):
        return "{} enters as {} starting with game {}".format(
            self.player, self.play_position, self.game_order
        )


class HomeSubstitution(Substitution):
    class Meta:
        proxy = True

    def __str__(self):
        return "{} enters as {} starting with game {}".format(
            self.player, self.play_position, self.game_order
        )


class ScoreSheet(models.Model):
    official = models.BooleanField(default=False)
    match = models.ForeignKey(Match)
    away_lineup = models.ManyToManyField(AwayLineupEntry, blank=True)
    home_lineup = models.ManyToManyField(HomeLineupEntry, blank=True)
    games = models.ManyToManyField(Game, blank=True)
    away_substitutions = models.ManyToManyField(AwaySubstitution)
    home_substitutions = models.ManyToManyField(HomeSubstitution)

    def __str__(self):
        return "{} ({})".format(self.match, self.id)

    def away_wins(self):
        return len(self.games.filter(winner='away'))

    def home_wins(self):
        return len(self.games.filter(winner='home'))


