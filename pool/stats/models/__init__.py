from django.db import models
from django.core.exceptions import ObjectDoesNotExist

from .playposition import PlayPosition, AwayPlayPosition, HomePlayPosition

import logging
logger = logging.getLogger(__name__)

away_home = ['away', 'home']


def get_default_season():
    try:
        return Season.objects.get(is_default=True)
    except ObjectDoesNotExist:
        return None


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
    email = models.EmailField(null=True, blank=True)

    def __str__(self):
        return self.display_name or "%s %s" % (self.first_name, self.last_name)

    class Meta:
        # Players with a display_name that sorts differently from their
        # first name will appear to be out of order in form selects.
        ordering = ['first_name', 'last_name']


class Division(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name


class Team(models.Model):
    # a default season that doesn't bork migrations would be nice
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    sponsor = models.ForeignKey(Sponsor, null=True, on_delete=models.CASCADE)
    division = models.ForeignKey(Division, null=True, limit_choices_to=models.Q(
        season__is_default=True), on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    players = models.ManyToManyField(Player, blank=True)
    away_wins = models.IntegerField(verbose_name='Away Wins', default=0)
    away_losses = models.IntegerField(verbose_name='Away Losses', default=0)
    home_wins = models.IntegerField(verbose_name='Home Wins', default=0)
    home_losses = models.IntegerField(verbose_name='Home Losses', default=0)
    win_percentage = models.FloatField(verbose_name='Win Percentage', default=0.0)
    ranking = models.IntegerField(null=True, blank=True)
    division_ranking = models.IntegerField(null=True, blank=True)
    rank_tie_breaker = models.IntegerField(default=0, null=True, blank=True)

    class Meta:
        ordering = ['name']

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
        away_score_sheets = ScoreSheet.objects.filter(
            match__away_team__exact=self, official__exact=True, match__playoff=False
        )
        for away_score_sheet in away_score_sheets:
            self.away_wins += len(away_score_sheet.games.filter(winner='away'))
            self.away_losses += len(away_score_sheet.games.filter(winner='home'))
        home_score_sheets = ScoreSheet.objects.filter(
            match__home_team__exact=self, official__exact=True, match__playoff=False
        )
        for home_score_sheet in home_score_sheets:
            self.home_wins += len(home_score_sheet.games.filter(winner='home'))
            self.home_losses += len(home_score_sheet.games.filter(winner='away'))
        denominator = self.home_losses + self.home_wins + self.away_losses + self.away_wins
        if denominator > 0:
            self.win_percentage = (self.home_wins + self.away_wins) / denominator

        self.save()

    def forfeit_wins(self):
        forfeit_wins = 0
        for home_away in ['away', 'home']:
            ss_filter_args = {'match__{}_team'.format(home_away): self}
            home_ss = ScoreSheet.objects.filter(official=1).filter(match__season=self.season).filter(
                **ss_filter_args
            )
            for s in home_ss:
                forfeit_wins += len(s.games.filter(winner=home_away).filter(forfeit=True))
        return forfeit_wins

    def find_score_sheets_against(self, other_teams, official=1):
        return ScoreSheet.objects.filter(
            official=official
        ).filter(
            models.Q(match__away_team__in=other_teams) & models.Q(match__home_team__id=self.id)
            |
            models.Q(match__home_team__in=other_teams) & models.Q(match__away_team__id=self.id)
        )

    def net_game_wins_against(self, other_teams, score_sheets=None):
        net_wins = 0

        # we need a shallow copy of other_teams here, so we can both call this function as a lambda, and
        # not alter the list in the calling context
        local_other_teams = [x for x in other_teams if x != self.id]
        if score_sheets is None:  # this is just here to allow passing in score sheets for tests
            score_sheets = self.find_score_sheets_against(local_other_teams)

        # find all the score sheets where this team is home, and one of the others is away, and vice versa
        for score_sheet in score_sheets:
            away_match = 1 if score_sheet.match.away_team == self else -1
            net_wins += score_sheet.away_wins() * away_match - score_sheet.home_wins() * away_match

        return net_wins

    @classmethod
    def update_rankings(cls, season_id):
        Team.update_teams_stats(season_id)
        # first, the divisions
        for division in Division.objects.filter(season_id=season_id):
            # print('ranking things for division {}/{}'.format(division, division.id))
            Team.rank_teams(Team.objects.filter(division=division).order_by('-win_percentage'), divisional=True)
            # TODO: there may be unresolved ties. how should we flag that?
        Team.rank_teams(Team.objects.filter(season_id=season_id).order_by('-win_percentage'))
        # TODO: same as above here

    def get_ranking(self, divisional):
        attribute = 'division_ranking' if divisional else 'ranking'
        return getattr(self, attribute)

    def set_ranking(self, value, divisional):
        attribute = 'division_ranking' if divisional else 'ranking'
        # print('previous ranking for {}: {}'.format(self, getattr(self, attribute)))
        setattr(self, attribute, value)
        self.save()
        # print('{} set to {} for team {}'.format(attribute, getattr(self, attribute), self ))

    @classmethod
    def find_ties(cls, queryset, attribute, divisional=False, set_rankings=False):
        inc = 0
        the_ties = []
        # print("\n".join([x.name for x in queryset]))
        while inc < len(queryset):
            offset = 1
            this_tie = [queryset[inc]]
            # print('checking for ties with: {}/{}'.format(
            #     queryset[inc],
            #     getattr(queryset[inc], attribute)
            # ))
            if inc == (len(queryset) - 1) or \
                    getattr(queryset[inc], attribute) != getattr(queryset[inc + offset], attribute):
                if set_rankings:
                    queryset[inc].set_ranking(inc + 1, divisional)
            while inc + offset < len(queryset) \
                    and getattr(queryset[inc], attribute) == getattr(queryset[inc + offset], attribute):
                this_tie.append(queryset[inc + offset])
                if set_rankings:
                    queryset[inc].set_ranking(inc + 1, divisional)
                    queryset[inc + offset].set_ranking(inc + 1, divisional)
                offset += 1
            if len(this_tie) > 1:
                the_ties.append(this_tie)
            inc += offset
        return the_ties

    @classmethod
    def break_tie(cls, tie, attribute, divisional=False, tie_arg=False, reverse_order=False):
        """

        :param tie: the tie that needs broken
        :param attribute: the attribute or method name we'll use to sort/break ties on this pass
        :param divisional: are we setting divisional rankings? or overall?
        :param tie_arg: does the method need the tie passed to it as an argument? really just for net_game_wins_against.
        :param reverse_order: does this tie-breaker sort people in the reverse order we want?
            it should be true for net_game_wins_against.
        :return: nothing. apply new rankings in-place.
        """

        def get_value(team):
            if tie_arg:
                return getattr(team, attribute)(tie)
            elif attribute == 'forfeit_wins':
                return team.forfeit_wins()
            else:
                return getattr(team, attribute)

        # print('breaking ties based on {}'.format(attribute))
        sorted_teams = sorted(tie, key=lambda team: get_value(team))
        if reverse_order:
            sorted_teams.reverse()

        inc = 0
        de_tying_array = []  # will be the number to add to the ranking
        # 0 for the 0th team + tied teams
        while inc < len(sorted_teams):
            offset = 1
            tiebreaker_value = get_value(sorted_teams[inc])
            de_tying_array.append(inc)

            while inc + offset < len(sorted_teams) and \
                    tiebreaker_value == \
                    get_value(sorted_teams[inc + offset]):
                de_tying_array.append(inc)
                offset += 1
                # print('bottom of the while: inc {} and offset: {}'.format(inc, offset))
            inc += offset
        rank_set_inc = 0
        for rank_change in de_tying_array:
            if rank_change:
                prev_rank = sorted_teams[rank_set_inc].get_ranking(divisional)
                sorted_teams[rank_set_inc].set_ranking(prev_rank + rank_change, divisional)
            rank_set_inc += 1

    @classmethod
    def rank_teams(cls, queryset, divisional=False):
        # first-order ordering

        the_ties = Team.find_ties(queryset, 'win_percentage', divisional, set_rankings=True)
        # now take the ties, the teams in them are ranked.
        # if a tie can be broken by the net game wins in matches against tied teams,
        # set/save the new ranking, then delete the ties

        for a_tie in the_ties:
            Team.break_tie(a_tie, 'net_game_wins_against', divisional, tie_arg=True, reverse_order=True)

        # there ought to be a way to preserve the ties, but it seems I am going to re-find them
        # to tie-break based on divisional rankings
        if not divisional:
            the_ties = Team.find_ties(queryset, 'ranking')
            for a_tie in the_ties:
                Team.break_tie(a_tie, 'division_ranking')

        # OK now, this is the last automatic tie-breaker.
        attribute = 'division_ranking' if divisional else 'ranking'
        the_ties = Team.find_ties(queryset, attribute, divisional)
        for a_tie in the_ties:
            Team.break_tie(a_tie, 'forfeit_wins', divisional)

        # norly, the last tie breaker is the rank_tie_breaker, which is populated manually, ie on a coin toss
        the_ties = Team.find_ties(queryset, attribute, divisional)
        for a_tie in the_ties:
            Team.break_tie(a_tie, 'rank_tie_breaker', divisional)

    @classmethod
    def update_teams_stats(cls, season_id):
        teams = cls.objects.filter(season=season_id)
        for this_team in teams:
            this_team.count_games()


class PlayerSeasonSummary(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    wins = models.IntegerField(verbose_name='Wins', default=0)
    losses = models.IntegerField(verbose_name='Losses', default=0)
    four_ohs = models.IntegerField(verbose_name='4-0s', default=0)
    table_runs = models.IntegerField(verbose_name='Table Runs', default=0)
    win_percentage = models.FloatField(verbose_name='Win Percentage', default=0.0, null=True)
    ranking = models.IntegerField(null=True)

    def __str__(self):
        return "{} {}".format(self.player, self.season)

    class Meta:
        ordering = ['-win_percentage']

    def team(self):
        return self.player.team_set.filter(season=self.season).first()

    def update_sweeps(self):
        # the occasional player may have played for more than one
        # team in a season ...
        score_sheets = ScoreSheet.objects.filter(
            models.Q(match__away_team__in=self.player.team_set.filter(season=self.season))
            |
            models.Q(match__home_team__in=self.player.team_set.filter(season=self.season))
        ).filter(official=1)
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
        all_summaries = cls.objects.filter(season=season_id).order_by('-win_percentage', '-wins')
        # remove the players with < the minimum number of games in the current season
        summaries = []
        for summary in all_summaries:
            if summary.wins + summary.losses >= summary.season.minimum_games:
                summaries.append(summary)
            else:
                summary.ranking = 0
                summary.save()
        inc = 0
        while inc < len(summaries):
            tie_count = 0
            while inc + tie_count < len(summaries):
                # the first clause below is to prevent us trying to compare something off the end of the list
                if (inc+tie_count+1 < len(summaries)) and \
                                summaries[inc].win_percentage == summaries[inc+tie_count+1].win_percentage and \
                                summaries[inc].wins == summaries[inc + tie_count + 1].wins:
                    tie_count += 1
                else:
                    break
            for i in range(0, tie_count + 1):
                summaries[inc+i].ranking = inc + 1
                summaries[inc+i].save()
            inc += tie_count + 1

    def update(self):
        games = Game.objects.filter(
            scoresheet__match__season_id=self.season
        ).filter(
            scoresheet__official=True
        ).filter(
            scoresheet__match__playoff=False
        ).filter(
            forfeit=False
        )
        away_wins = games.filter(away_player=self.player).filter(winner='away')
        home_wins = games.filter(home_player=self.player).filter(winner='home')

        away_losses = games.filter(away_player=self.player).filter(winner='home')
        home_losses = games.filter(home_player=self.player).filter(winner='away')

        self.team = self.player.team_set.filter(season=self.season).first()

        logger.debug("{} has {} wins and {} losses".format(self, self.wins, self.losses))
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
        # find all the players on teams in this season
        teams = Team.objects.filter(season=season_id)
        for team in teams:
            for player in team.players.all():
                summaries = cls.objects.filter(season=season_id, player=player)
                if not len(summaries):
                    cls(season=Season.objects.get(id=season_id), player=player).save()

        for summary in cls.objects.filter(season=season_id):
            summary.update()
        cls.update_rankings(season_id)


class Week(models.Model):
    # a default season that doesn't bork migrations would be nice
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    date = models.DateField(null=True, blank=True)
    name = models.CharField(max_length=32, null=True)

    def __str__(self):
        return "{}".format(self.name)

    @classmethod
    def get_weeks_in_season(cls, before_after, week):
        comp_args = {
            'season_id': week.season,
            'date__{}'.format('lt' if before_after == 'before' else 'gt'): week.date
        }
        weeks = cls.objects.filter(**comp_args).order_by('date')
        if before_after == 'before':
            return list(weeks)[-1] if weeks else None
        else:
            return weeks[0] if weeks else None

    def next(self):
        return self.get_weeks_in_season(before_after='after', week=self)

    def previous(self):
        return self.get_weeks_in_season(before_after='before', week=self)

    def unused_teams(self):
        matches_this_week = Match.objects.filter(week=self)
        used_teams = set([])
        for m in matches_this_week:
            used_teams.add(m.away_team.id)
            used_teams.add(m.home_team.id)
        return Team.objects.filter(season__is_default=True).exclude(id__in=used_teams)

    def used_teams(self, teams=[]):
        matches_this_week = Match.objects.filter(week=self)
        used_teams = set([])
        for m in matches_this_week:
            if hasattr(m.away_team, 'id') and m.away_team.id not in teams:
                used_teams.add(m.away_team.id)
            if hasattr(m.home_team, 'id') and m.home_team.id not in teams:
                used_teams.add(m.home_team.id)
        return Team.objects.filter(season__is_default=True).filter(id__in=used_teams)


class AwayTeam(Team):
    class Meta:
        proxy = True


class HomeTeam(Team):
    class Meta:
        proxy = True


class WeekDivisionMatchup(models.Model):

    week = models.ForeignKey(Week, on_delete=models.CASCADE, null=True)
    away_division = models.ForeignKey(
        Division,
        on_delete=models.CASCADE,
        limit_choices_to=models.Q(season__is_default=True),
        related_name='away_division',
    )
    home_division = models.ForeignKey(
        Division,
        on_delete=models.CASCADE,
        limit_choices_to=models.Q(season__is_default=True),
        related_name='home_division',
    )

    def __str__(self):
        return '{} @ {}'.format(self.away_division, self.home_division)


class Match(models.Model):
    # the `is_default` season being the default is set in the admin, rather than here,
    # doing it here breaks generating migrations with an empty database.
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    week = models.ForeignKey(Week, limit_choices_to=models.Q(season__is_default=True), on_delete=models.CASCADE)
    home_team = models.ForeignKey(
        'HomeTeam',
        limit_choices_to=models.Q(season__is_default=True),
        related_name='home_team',
        blank=True, null=True,
        on_delete=models.CASCADE
    )
    away_team = models.ForeignKey(
        'AwayTeam',
        limit_choices_to=models.Q(season__is_default=True),
        related_name='away_team',
        blank=True, null=True,
        on_delete=models.CASCADE
    )
    playoff = models.BooleanField(default=False)

    def __str__(self):
        # return "{} @ {} ({} {})".format(self.away_team, self.home_team, self.season, self.week)
        return "{} @ {}".format(self.away_team, self.home_team)

    class Meta:
        verbose_name = 'Match'
        verbose_name_plural = 'Matches'


class AwayPlayer(Player):
    class Meta:
        proxy = True


class HomePlayer(Player):
    class Meta:
        proxy = True


class GameOrder(models.Model):
    away_position = models.ForeignKey(
        AwayPlayPosition,
        related_name='away_position',
        on_delete=models.CASCADE,
    )
    home_position = models.ForeignKey(
        HomePlayPosition,
        related_name='home_position',
        on_delete=models.CASCADE,
    )
    home_breaks = models.BooleanField(default=True)
    order = models.IntegerField(null=True)
    tiebreaker = models.BooleanField(default=False)

    def __str__(self):
        return "{} ({} vs {})".format(self.order, self.away_position, self.home_position)

    class Meta:
        # the default/primary key sort is sometimes wrong
        ordering = ['order']


class Game(models.Model):
    away_player = models.ForeignKey(
        AwayPlayer,
        null=True,
        blank=True,
        related_name='away_player',
        on_delete=models.CASCADE,
    )
    home_player = models.ForeignKey(
        HomePlayer,
        null=True,
        blank=True,
        related_name='home_player',
        on_delete=models.CASCADE,
    )
    winner = models.CharField(max_length=4, blank=True)
    order = models.ForeignKey(GameOrder, null=True, on_delete=models.CASCADE)
    table_run = models.BooleanField(default=False)
    forfeit = models.BooleanField(default=False)


class LineupEntry(models.Model):
    player = models.ForeignKey(Player, null=True, blank=True, on_delete=models.CASCADE)
    position = models.ForeignKey(PlayPosition, null=True, on_delete=models.CASCADE)


class AwayLineupEntry(LineupEntry):
    class Meta:
        proxy = True


class HomeLineupEntry(LineupEntry):
    class Meta:
        proxy = True


class Substitution(models.Model):
    game_order = models.ForeignKey(GameOrder, on_delete=models.CASCADE)
    player = models.ForeignKey(Player, null=True, blank=True, on_delete=models.CASCADE)
    play_position = models.ForeignKey(PlayPosition, null=True, blank=True, on_delete=models.CASCADE)


class AwaySubstitution(Substitution):
    class Meta:
        proxy = True

    def __str__(self):
        return "{} enters as {} starting with game {}".format(
            self.player, self.play_position.away_name, self.game_order
        )


class HomeSubstitution(Substitution):
    class Meta:
        proxy = True

    def __str__(self):
        return "{} enters as {} starting with game {}".format(
            self.player, self.play_position.home_name, self.game_order
        )


class ScoreSheet(models.Model):

    MATCH_STATES = (
        (0, 'New'),
        (1, 'Official'),
        (2, 'Needs Changes'),
    )

    official = models.IntegerField(default=0, choices=MATCH_STATES, verbose_name='Status')
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='scoresheets')
    creator_session = models.CharField(max_length=16, null=True, blank=True)
    away_lineup = models.ManyToManyField(
        AwayLineupEntry,
        blank=True,
        related_name='away_lineup',
    )
    home_lineup = models.ManyToManyField(
        HomeLineupEntry,
        blank=True,
        related_name='home_lineup',
    )
    games = models.ManyToManyField(Game, blank=True)
    away_substitutions = models.ManyToManyField(
        AwaySubstitution,
        related_name='away_substitution',
    )
    home_substitutions = models.ManyToManyField(
        HomeSubstitution,
        related_name='home_substitution',
    )
    comment = models.TextField(max_length=500, blank=True)
    complete = models.BooleanField(default=False)

    def __str__(self):
        return "{}".format(self.match)

    def away_wins(self):
        return len(self.games.filter(winner='away'))

    def home_wins(self):
        return len(self.games.filter(winner='home'))

    def wins(self, away_home):
        return len(self.games.filter(winner=away_home))

    def initialize_lineup(self):
        lineup_positions = PlayPosition.objects.filter(tiebreaker=False)
        if self.match.playoff:
            lineup_positions = PlayPosition.objects.all()
        for lineup_position in lineup_positions:
            ale = AwayLineupEntry(position=lineup_position)
            ale.save()
            hle = HomeLineupEntry(position=lineup_position)
            hle.save()
            self.away_lineup.add(ale)
            self.home_lineup.add(hle)
        self.save()

    def initialize_games(self):
        # now create games, per the game order table
        for g in GameOrder.objects.filter(tiebreaker=False):
            game = Game()
            game.order = g
            game.save()
            self.games.add(game)
        if self.match.playoff:
            game = Game()
            game.order = GameOrder.objects.get(tiebreaker=True)
            game.save()
            self.games.add(game)

        self.save()

    def copy_game_orders_to_positions(self):
        """
        This ugly hack allows substitutions to be set by just game order, instead of
         also specifying the play position.
        """
        for away_home in ['away', 'home']:
            list_subs = getattr(self, '{}_substitutions'.format(away_home))
            for substitution in list_subs.all():
                position_m = getattr(substitution.game_order, '{}_position'.format(away_home))
                substitution.play_position = position_m
                substitution.save()

    def set_games(self):
        self.copy_game_orders_to_positions()
        for game in self.games.all():
            logger.debug("working on game {} from {}".format(game.order, self.match))

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

        lineup_entries = getattr(self, '{}_lineup'.format(away_home)).\
            filter(
                position__tiebreaker=False).\
            exclude(
                player__isnull=True
            )
        substitutions = getattr(self, '{}_substitutions'.format(away_home)).all()

        players = [x.player for x in lineup_entries]
        [players.append(y.player) for y in substitutions]
        for player in players:
            summary = {
                'player': player,
            }
            summary.update(self.player_summary(
                a_player=player
            ))
            player_score_sheet_summaries.append(summary)
        return player_score_sheet_summaries

    def check_wins_regular_season(self):

        issues = []

        # for non-playoff matches, check for there being lineup length * lineup length wins
        wins = dict.fromkeys(away_home, 0)
        losses = dict.fromkeys(away_home, 0)

        # expected_wins = len(self.home_lineup.exclude(player=None)) * len(self.away_lineup.exclude(player=None))
        away_lineup_player_count = len(self.away_lineup.exclude(player=None))
        home_lineup_player_count = len(self.home_lineup.exclude(player=None))
        away_lineup_length = len(self.away_lineup.all())
        home_lineup_length = len(self.home_lineup.all())

        # if there are missing players on *both* teams, then reduce the expected wins by the multiple of the 2
        expected_wins = away_lineup_length * home_lineup_length - \
            (away_lineup_length - away_lineup_player_count) * \
            (home_lineup_length - home_lineup_player_count)

        for game in self.games.all():
            if game.winner:
                wins[game.winner] += 1
            other = [x for x in away_home if x != game.winner]
            losses[other[0]] += 1

        if expected_wins != wins['away'] + wins['home']:
            issues += ['expected {} non-forfeit wins, found {}'.format(expected_wins, wins['away'] + wins['home'])]
        return issues

    def check_unmarked_forfeits(self):

        from operator import xor
        issues = []

        # check for games where a player is None, but it is not marked as a forfeit
        unmarked_forfeit_games = []
        for game in self.games.all():
            if xor(bool(game.away_player), bool(game.home_player)) and not game.forfeit:
                unmarked_forfeit_games.append(game.order)
        if unmarked_forfeit_games:
            issues += ["{} is/are missing a player, but not marked as a forfeit".format(', '.join(
                    [str(x) for x in unmarked_forfeit_games]
            ))]
        return issues

    def check_playoff_win_count(self):
        """
        Check that there are exactly len(non-tiebreaker games) / 2 + 1 wins by one team
        :return:
        """

        issues = []

        win_count = 1 + int(len(GameOrder.objects.filter(tiebreaker=False)) / 2)
        home_wins = self.home_wins()
        away_wins = self.away_wins()
        if win_count != home_wins and win_count != away_wins:
            issues += ["Playoff matches should have exactly {} wins".format(win_count)]

        return issues

    def self_check(self, mark_for_review=False):

        """

        :return: a list of issues with the score sheet
        """

        issues = []
        issues += self.check_unmarked_forfeits()
        if self.match.playoff:
            issues += self.check_playoff_win_count()
        else:
            issues += self.check_wins_regular_season()

        if len(issues) and mark_for_review:
            self.status = 2  # needs changes

        return issues
