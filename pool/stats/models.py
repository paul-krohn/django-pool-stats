from django.db import models
import itertools


def count_forfeit_wins(team):
    # we need the games where this team is the away_home team, where
    # this team 'won' the game, and where the game was a forfeit
    forfeit_wins = 0
    for away_home in ['away', 'home']:
        match_args = {
            "scoresheet__match__{}_team".format(away_home): team
        }
        games = Game.objects.filter(
            scoresheet__match__season_id=team.season
        ).filter(
            **match_args
        ).filter(
            scoresheet__official=True
        ).filter(
            forfeit=True
        ).filter(
            winner=away_home
        )
        forfeit_wins += len(games)
        print("{} had {} {} forfeit wins".format(team, len(games), away_home))
    return forfeit_wins


def tie_break_team_pair(teams):
    score_sheets = ScoreSheet.objects.filter(
        models.Q(match__away_team__in=[teams[0], teams[1]])
        &
        models.Q(match__home_team__in=[teams[0], teams[1]])
    ).filter(official=True)
    a_wins = 0
    b_wins = 0
    for score_sheet in score_sheets:
        if score_sheet.away_wins() == score_sheet.home_wins():
            continue
        elif score_sheet.away_wins() > score_sheet.home_wins():
            if score_sheet.match.away_team == teams[0]:
                a_wins += 1
            else:
                b_wins += 1
        else:
            if score_sheet.match.away_team == teams[0]:
                b_wins += 1
            else:
                a_wins += 1
    if a_wins == b_wins:
        # do the forfeit comparison, but for now, return them in the order they were passed in
        print("can't rank these teams based on head-to-head; wins are {} to {}".format(a_wins, b_wins))
        a_forfeit_wins = count_forfeit_wins(teams[0])
        b_forfeit_wins = count_forfeit_wins(teams[1])
        if a_forfeit_wins == b_forfeit_wins:
            return None
        elif a_forfeit_wins > b_forfeit_wins:
            return teams
        else:
            return [teams[1], teams[0]]
    elif a_wins > b_wins:
        return teams
    else:
        return [teams[1], teams[0]]


def tie_break_teams(teams):
    """
    Given a queryset of teams, tie-break them. Return the teams in the ranking order based on
    head-to-head matches.
    Detect when a>b, b>c, and c>a, in which case return None.
    :param teams:
    :return: sorted list of teams
    """
    print("tie_break_teams was passed: {}".format(teams))

    combination_count = 0
    print("the possible combinations are:")
    for subset in itertools.combinations(teams, 2):
        print(subset)
        combination_count += 1
    print("there are {} combinations".format(combination_count))
    for subset in itertools.combinations(teams, 2):
        ordered_teams = tie_break_team_pair(subset)
        if ordered_teams is not None:
            print("the tie-broken pair is: {}".format(ordered_teams))
        else:
            print("{} and {} are tied".format(subset[0], subset[1]))

    return teams


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
    minimum_games = models.IntegerField(null=True)

    def __str__(self):
        return self.name


class Player(models.Model):
    first_name = models.CharField(max_length=64)
    last_name = models.CharField(max_length=64)
    display_name = models.CharField(max_length=128, null=True, blank=True)

    def __str__(self):
        return self.display_name or "%s %s" % (self.first_name, self.last_name)

    class Meta:
        # Players with a display_name that sorts differently from their
        # first name will appear to be out of order in form selects.
        ordering = ['first_name', 'last_name']


class PlayerSeasonSummary(models.Model):
    player = models.ForeignKey(Player)
    season = models.ForeignKey(Season)
    wins = models.IntegerField(verbose_name='Wins', default=0)
    losses = models.IntegerField(verbose_name='Losses', default=0)
    four_ohs = models.IntegerField(verbose_name='4-0s', default=0)
    table_runs = models.IntegerField(verbose_name='Table Runs', default=0)
    win_percentage = models.FloatField(verbose_name='Win Percentage', default=0.0)
    ranking = models.IntegerField(null=True)

    def __str__(self):
        return "{} {}".format(self.player, self.season)

    class Meta:
        ordering = ['-win_percentage']

    def update_sweeps(self):
        # the occasional player may have played for more than one
        # team in a season ...
        score_sheets = ScoreSheet.objects.filter(
            models.Q(match__away_team__in=self.player.team_set.filter(season=self.season))
            |
            models.Q(match__home_team__in=self.player.team_set.filter(season=self.season))
        ).filter(official=True)
        sweeps = 0

        for score_sheet in score_sheets:
            for away_home in ['away', 'home']:
                score_sheet_filter_args = {'{}_player'.format(away_home): self.player}
                if len(score_sheet.games.filter(
                    **score_sheet_filter_args
                ).filter(
                    winner=away_home
                )) == 4:
                    sweeps += 1
        self.four_ohs = sweeps
        self.save()

    @classmethod
    def update_rankings(cls, season_id):
        all_summaries = cls.objects.filter(season=season_id).order_by('-win_percentage')
        # remove the players with < the minimum number of games in the current season
        summaries = []
        for summary in all_summaries:
            if summary.wins + summary.losses >= summary.season.minimum_games:
                summaries.append(summary)
            else:
                summary.ranking = 0
                summary.save()
        inc = 0
        while inc < len(summaries) - 1:
            offset = 1
            summaries[inc].ranking = inc + 1
            summaries[inc].save()
            print("{} gets ranking {}".format(summaries[inc], summaries[inc].ranking))
            while inc + offset < len(summaries) and \
                    summaries[inc].win_percentage == summaries[inc+offset].win_percentage:
                summaries[inc+offset].ranking = inc + 1
                summaries[inc+offset].save()
                print("{} gets ranking {}".format(summaries[inc+offset], summaries[inc].ranking))
                offset += 1
            inc += offset

    def update(self):
        games = Game.objects.filter(
            scoresheet__match__season_id=self.season
        ).filter(
            scoresheet__official=True
        ).filter(
            forfeit=False
        )
        away_wins = games.filter(away_player=self.player).filter(winner='away')
        home_wins = games.filter(home_player=self.player).filter(winner='home')

        away_losses = games.filter(away_player=self.player).filter(winner='home')
        home_losses = games.filter(home_player=self.player).filter(winner='away')

        print("{} has {} wins and {} losses".format(self, self.wins, self.losses))
        self.wins = len(away_wins) + len(home_wins)
        self.losses = len(away_losses) + len(home_losses)
        self.win_percentage = None
        if self.wins + self.losses > 0:
            self.win_percentage = self.wins / (self.wins + self.losses)

        self.table_runs = len(away_wins.filter(table_run=True)) + len(home_wins.filter(table_run=True))

        self.update_sweeps()

        self.save()

    @classmethod
    def update_all(cls, season_id):
        for summary in cls.objects.filter(season=season_id):
            summary.update()
        cls.update_rankings(season_id)


class Division(models.Model):
    season = models.ForeignKey(Season)
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

    def rank(self):
        teams = self.team_set.order_by('-win_percentage')
        print("there are {} teams to rank in division {}: {}".format(len(teams), self, teams))
        inc = 0
        offset = 0
        while inc <= len(teams) - 1:
            print("inc is {}".format(inc))
            if teams[inc].win_percentage == 0.0:
                print("{} has no record, not ranking them".format(teams[inc]))
                teams[inc].ranking_division = len(teams)
                teams[inc].save()
                inc += 1
            else:
                tied_teams = self.team_set.filter(win_percentage=teams[inc].win_percentage)
                if len(tied_teams) == 1:
                    print("there are no ties at {}".format(teams[inc].win_percentage))
                    print("{} is ranked {} in division {}".format(teams[inc], inc + 1, self))
                    # one team in the division/no ties, carry on
                    teams[inc].ranking_division = inc + 1
                    teams[inc].save()
                    inc += 1
                else:
                    print("there is a tie at {}".format(teams[inc].win_percentage))
                    ranked_teams = tie_break_teams(tied_teams)
                    for team in ranked_teams:
                        print("ranking {} at {}, inc is {}".format(teams[inc], inc + offset + 1, inc))
                        team.ranking_division = inc + offset + 1
                        team.save()
                        offset += 1
                    inc += offset


class Team(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    sponsor = models.ForeignKey(Sponsor, null=True)
    division = models.ForeignKey(Division, null=True)
    name = models.CharField(max_length=200)
    players = models.ManyToManyField(Player, blank=True)
    away_wins = models.IntegerField(verbose_name='Away Wins', default=0)
    away_losses = models.IntegerField(verbose_name='Away Losses', default=0)
    home_wins = models.IntegerField(verbose_name='Home Wins', default=0)
    home_losses = models.IntegerField(verbose_name='Home Losses', default=0)
    win_percentage = models.FloatField(verbose_name='Win Percentage', default=0.0)
    ranking = models.IntegerField(null=True)
    ranking_division = models.IntegerField(null=True)

    class Meta:
        ordering = ['-ranking']

    def __str__(self):
        return "{}".format(self.name)

    def wins(self):
        return self.away_wins + self.home_wins

    def losses(self):
        return self.away_losses + self.home_losses

    def count_games(self):
        """
        Count the summary stats for a team
        :return:
        """
        self.away_wins = 0
        self.away_losses = 0
        self.home_wins = 0
        self.home_losses = 0
        self.win_percentage = 0.0

        # first, matches involving the team as away team
        away_score_sheets = ScoreSheet.objects.filter(match__away_team__exact=self, official__exact=True)
        for away_score_sheet in away_score_sheets:
            self.away_wins += len(away_score_sheet.games.filter(winner='away'))
            self.away_losses += len(away_score_sheet.games.filter(winner='home'))
        home_score_sheets = ScoreSheet.objects.filter(match__home_team__exact=self, official__exact=True)
        for home_score_sheet in home_score_sheets:
            self.home_wins += len(home_score_sheet.games.filter(winner='home'))
            self.home_losses += len(home_score_sheet.games.filter(winner='away'))
        denominator = self.home_losses + self.home_wins + self.away_losses + self.away_wins
        if denominator > 0:
            self.win_percentage = (self.home_wins + self.away_wins) / denominator

        self.save()

    @classmethod
    def rank_teams(cls, season_id):
        # we need to tie-break these teams, based on the division rank, which requires the
        # record between the teams and/or a manual tie-break entry; so we start by
        # division-ranking the teams
        for division in Division.objects.all():
            division.rank()

        teams = cls.objects.filter(season=season_id).order_by('-win_percentage', 'ranking_division')
        print("there are {} teams to rank: {}".format(len(teams), teams))
        # inc = 0
        # while inc < len(teams) - 1:
        #     offset = 1
        #     teams[inc].ranking = inc + 1
        #     teams[inc].save()
        #     print("{} gets ranking {}".format(teams[inc], teams[inc].ranking))
        #     while inc + offset < len(teams) and teams[inc].win_percentage == teams[inc+offset].win_percentage:
        #         # now we need to tie-break based on division ranking
        #         if teams[inc].ranking_division == teams[inc+offset].ranking_division:
        #             # tie-break based on opposing records required
        #             pass
        #         else:
        #             # in this case, < represents a better ranking
        #             print("tie-breaking {} and {} based on division rankings, which are {} and {}".format(teams[inc], teams[inc+offset], teams[inc].ranking_division, teams[inc+offset].ranking_division))
        #             if teams[inc].ranking_division < teams[inc+offset].ranking_division:
        #                 teams[inc].ranking = inc + offset
        #                 teams[inc + offset].ranking = inc + offset + 1
        #         offset += 1
        #     inc += offset
        # ranked_teams = cls.objects.filter(season=season_id).order_by('ranking')
        # for team in ranked_teams:
        #     print("team: {} rank: {}".format(team, team.ranking))

    @classmethod
    def update_teams_stats(cls, season_id):
        teams = cls.objects.filter(season=season_id)
        for this_team in teams:
            this_team.count_games()
        cls.rank_teams(season_id)


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
    home_breaks = models.BooleanField(default=True)
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
    creator_session = models.CharField(max_length=16, null=True, blank=True)
    away_lineup = models.ManyToManyField(AwayLineupEntry, blank=True)
    home_lineup = models.ManyToManyField(HomeLineupEntry, blank=True)
    games = models.ManyToManyField(Game, blank=True)
    away_substitutions = models.ManyToManyField(AwaySubstitution)
    home_substitutions = models.ManyToManyField(HomeSubstitution)
    comment = models.TextField(max_length=500, blank=True)
    complete = models.BooleanField(default=False)

    def __str__(self):
        return "{} ({})".format(self.match, self.id)

    def away_wins(self):
        return len(self.games.filter(winner='away'))

    def home_wins(self):
        return len(self.games.filter(winner='home'))

    def initialize_lineup(self):
        for lineup_position in PlayPosition.objects.all():
            ale = AwayLineupEntry(position=lineup_position)
            ale.save()
            hle = HomeLineupEntry(position=lineup_position)
            hle.save()
            self.away_lineup.add(ale)
            self.home_lineup.add(hle)
        self.save()

    def initialize_games(self):
        # now create games, per the game order table
        for g in GameOrder.objects.all():
            game = Game()
            game.order = g
            game.table_run = False
            game.forfeit = False
            game.save()
            self.games.add(game)
        self.save()

    def set_games(self):
        for game in self.games.all():
            print("working on game {} from {}".format(game.order, self.match))

            # set the players for the game; have to convert Player instances to Home/AwayPlayer instances
            away_player_position = self.away_lineup.filter(position_id__exact=game.order.away_position.id)[0]
            if away_player_position.player is not None:
                game.away_player = AwayPlayer.objects.get(id=away_player_position.player.id)
            home_player_position = self.home_lineup.filter(position_id__exact=game.order.home_position.id)[0]
            if home_player_position.player is not None:
                game.home_player = HomePlayer.objects.get(id=home_player_position.player.id)

            # check substitutions based on their being for <= this lineup position; over-ride the player
            for away_substitution in self.away_substitutions.all():
                if away_substitution.game_order.id <= game.order.id and \
                        away_substitution.play_position == game.order.away_position:
                    game.away_player = AwayPlayer.objects.get(id=away_substitution.player.id)
            for home_substitution in self.home_substitutions.all():
                if home_substitution.game_order.id <= game.order.id and \
                        home_substitution.play_position == game.order.home_position:
                    game.home_player = HomePlayer.objects.get(id=home_substitution.player.id)
            game.save()

    def player_summary(self, a_player):

        away_wins = self.games.filter(winner='away', away_player=a_player, forfeit=False)
        away_losses = self.games.filter(winner='home', away_player=a_player, forfeit=False)

        home_wins = self.games.filter(winner='home', home_player=a_player, forfeit=False)
        home_losses = self.games.filter(winner='away', home_player=a_player, forfeit=False)

        return {
            'wins': len(away_wins.all()) + len(home_wins.all()),
            'losses': len(away_losses.all()) + len(home_losses.all()),
            'table_runs': len(away_wins.filter(table_run=True)) + len(home_wins.filter(table_run=True)),
        }

    def player_summaries(self, away_home):

        player_score_sheet_summaries = []
        if away_home == 'away':
            lineup_entries = self.away_lineup.all()
        else:
            lineup_entries = self.home_lineup.all()
        for lineup_entry in lineup_entries:
            if lineup_entry.player is None:
                continue
            summary = {
                'player': lineup_entry.player,
            }
            summary.update(self.player_summary(
                a_player=lineup_entry.player
            ))
            player_score_sheet_summaries.append(summary)
        return player_score_sheet_summaries
