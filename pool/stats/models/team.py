
from django.db import models

from .division import Division
from .player import Player
from .scoresheet import ScoreSheet
from .season import Season
from .sponsor import Sponsor
from .table import Table


from .globals import away_home, logger


class Team(models.Model):
    # a default season that doesn't bork migrations would be nice
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    # sponsor = models.ForeignKey(Sponsor, null=True, on_delete=models.CASCADE)
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
    table = models.ForeignKey(Table, blank=True, null=True, on_delete=models.CASCADE)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return "{}".format(self.name)

    def sponsor(self):
        return self.table.venue

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
        for home_away in away_home:
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


class AwayTeam(Team):
    class Meta:
        proxy = True


class HomeTeam(Team):
    class Meta:
        proxy = True