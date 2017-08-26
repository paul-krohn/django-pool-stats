from django.db import models
from django.core.exceptions import ObjectDoesNotExist
import logging
from math import log
from random import shuffle

logger = logging.getLogger(__name__)


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


class PlayerSeasonSummary(models.Model):
    player = models.ForeignKey(Player)
    season = models.ForeignKey(Season)
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
            logging.debug("{} gets ranking {}".format(summaries[inc], summaries[inc].ranking))
            while inc + offset < len(summaries) and \
                    summaries[inc].win_percentage == summaries[inc+offset].win_percentage:
                summaries[inc+offset].ranking = inc + 1
                summaries[inc+offset].save()
                logger.debug("{} gets ranking {}".format(summaries[inc+offset], summaries[inc].ranking))
                offset += 1
            inc += offset

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


class Division(models.Model):
    season = models.ForeignKey(Season)
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name


class Team(models.Model):
    # a default season that doesn't bork migrations would be nice
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    sponsor = models.ForeignKey(Sponsor, null=True)
    division = models.ForeignKey(Division, null=True, limit_choices_to=models.Q(season__is_default=True))
    name = models.CharField(max_length=200)
    players = models.ManyToManyField(Player, blank=True)
    away_wins = models.IntegerField(verbose_name='Away Wins', default=0)
    away_losses = models.IntegerField(verbose_name='Away Losses', default=0)
    home_wins = models.IntegerField(verbose_name='Home Wins', default=0)
    home_losses = models.IntegerField(verbose_name='Home Losses', default=0)
    win_percentage = models.FloatField(verbose_name='Win Percentage', default=0.0)
    ranking = models.IntegerField(null=True, blank=True)
    rank_tie_breaker = models.IntegerField(null=True, blank=True)

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

    @classmethod
    def rank_teams(cls, season_id):
        teams = cls.objects.filter(season=season_id).order_by('-win_percentage', '-rank_tie_breaker')
        # sorted(teams, key=attrgetter('win_percentage'))
        logger.debug(teams)
        logger.debug("there are {} teams to rank ".format(len(teams)))
        inc = 0
        while inc < len(teams):
            offset = 1
            teams[inc].ranking = inc + 1
            teams[inc].save()
            logger.debug("{} gets ranking {}".format(teams[inc], teams[inc].ranking))
            while inc + offset < len(teams) and teams[inc].win_percentage == teams[inc+offset].win_percentage \
                    and teams[inc].rank_tie_breaker == teams[inc+offset].rank_tie_breaker:
                teams[inc+offset].ranking = inc + 1
                teams[inc+offset].save()
                logger.debug("{} gets ranking {}".format(teams[inc+offset], teams[inc].ranking))
                offset += 1
            inc += offset

    @classmethod
    def update_teams_stats(cls, season_id):
        teams = cls.objects.filter(season=season_id)
        for this_team in teams:
            this_team.count_games()
        cls.rank_teams(season_id)


class Week(models.Model):
    # a default season that doesn't bork migrations would be nice
    season = models.ForeignKey(Season)
    date = models.DateField(null=True, blank=True)
    name = models.CharField(max_length=32, null=True)

    def __str__(self):
        return "{}".format(self.name)


class AwayTeam(Team):
    class Meta:
        proxy = True


class HomeTeam(Team):
    class Meta:
        proxy = True


class Match(models.Model):
    # a default season that doesn't bork migrations would be nice
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    week = models.ForeignKey(Week, limit_choices_to=models.Q(season__is_default=True))
    home_team = models.ForeignKey(
        'HomeTeam',
        limit_choices_to=models.Q(season__is_default=True),
        related_name='home_team',
    )
    away_team = models.ForeignKey(
        'AwayTeam',
        limit_choices_to=models.Q(season__is_default=True),
        related_name='away_team',
    )
    playoff = models.BooleanField(default=False)

    def __str__(self):
        return "{} @ {} ({} {})".format(self.away_team, self.home_team, self.season, self.week)

    class Meta:
        verbose_name = 'Match'
        verbose_name_plural = 'Matches'


class PlayPosition(models.Model):
    home_name = models.CharField(max_length=16)
    away_name = models.CharField(max_length=16)
    name = models.CharField(max_length=16)
    tiebreaker = models.BooleanField(default=False)

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
    away_position = models.ForeignKey(
        AwayPlayPosition,
        related_name='away_position',
    )
    home_position = models.ForeignKey(
        HomePlayPosition,
        related_name='home_position',
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
    )
    home_player = models.ForeignKey(
        HomePlayer,
        null=True,
        blank=True,
        related_name='home_player',
    )
    winner = models.CharField(max_length=4, blank=True)
    order = models.ForeignKey(GameOrder, null=True)
    table_run = models.BooleanField(default=False)
    forfeit = models.BooleanField(default=False)


class LineupEntry(models.Model):
    player = models.ForeignKey(Player, null=True, blank=True)
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
    play_position = models.ForeignKey(PlayPosition, null=True, blank=True)


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
    official = models.BooleanField(default=False)
    match = models.ForeignKey(Match)
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

    def initialize_lineup(self):
        for lineup_position in PlayPosition.objects.filter(tiebreaker=False):
            ale = AwayLineupEntry(position=lineup_position)
            ale.save()
            hle = HomeLineupEntry(position=lineup_position)
            hle.save()
            self.away_lineup.add(ale)
            self.home_lineup.add(hle)
        if self.match.playoff:
            lineup_position = PlayPosition.objects.get(tiebreaker=True)
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
        if away_home == 'away':
            lineup_entries = self.away_lineup.filter(position__tiebreaker=False)
        else:
            lineup_entries = self.home_lineup.filter(position__tiebreaker=False)
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


class TournamentPlayPosition(models.Model):
    position = models.IntegerField()
    player = models.ForeignKey(Player, null=True)  # if null, is a bye?

    def __str__(self):
        if self.player is not None:
            return self.player.__str__()
        else:
            return 'Bye'


class TournamentMatch(models.Model):
    play_order = models.IntegerField()
    bye = models.BooleanField(default=False)
    player_a = models.ForeignKey(
        Player,
        related_name='player_a',
        null=True,
    )
    player_b = models.ForeignKey(
        Player,
        related_name='player_b',
        null=True,
    )
    winner = models.ForeignKey(
        Player,
        related_name='match_winning_player',
        null=True,
    )
    player_a_match = models.ForeignKey(
        'self',
        related_name='player_a_source_match',
        null=True,
    )
    player_b_match = models.ForeignKey(
        'self',
        related_name='player_b_source_match',
        null=True,
    )

    def desc(self):
        pas = 'winner of ' + self.player_a_match if self.player_a_match.winner is None else self.player_a_match.winner
        pbs = 'winner of ' + self.player_b_match if self.player_b_match.winner is None else self.player_b_match.winner
        return '{} vs {}'.format(pas, pbs)


class Tournament(models.Model):
    FORMATS = (
        (0, 'Single Elimination'),
        (1, 'Double Elimination'),
        # scotch doubles ??
    )
    season = models.ForeignKey(Season)
    name = models.CharField(max_length=128)
    date = models.DateField()
    players = models.ManyToManyField(Player, blank=True)
    play_positions = models.ManyToManyField(TournamentPlayPosition, blank=True)
    play_format = models.IntegerField(choices=FORMATS)
    race_to = models.IntegerField()
    matches = models.ManyToManyField(TournamentMatch, blank=True)

    def __str__(self):
        return "{}".format(self.name)

    def bracket_size(self):
        player_count = len(list(self.players.all()))
        start = int(log(player_count, 2))
        if player_count == 2 ** start:  # there happens to be power-of-2 players
            return 2 ** start
        else:
            return 2 ** (start + 1)

    def create_play_positions(self):
        for x in range(0, self.bracket_size()):
            tpp = TournamentPlayPosition(position=x)
            tpp.save()
            self.play_positions.add(tpp)
        self.save()

    def assign_players(self):
        player_order = [x for x in range(0, self.bracket_size())]
        shuffle(player_order)
        # print('player order is: {}'.format(player_order))
        # print('players are: {}'.format(self.players.all()))
        for player in self.players.all():
            position = self.play_positions.get(position=player_order.pop())
            position.player = player
            position.save()
        # now the remaining play positions have no player set, ie are
        # byes. TODO: allow late-entry players into un-realized byes

    def create_tournament_matches(self):
        for match_number in range(0, self.get_number_of_matches()):
            m = TournamentMatch(
                    play_order=match_number,
            )
            half_bracket = int(self.bracket_size() / 2)
            # set up first-round matches
            if match_number < half_bracket:
                m.player_a = self.play_positions.all()[match_number].player
                m.player_b = self.play_positions.all()[self.bracket_size() - 1 - match_number].player
            # subsequent-round matches, holds through at least 16-player SE bracket
            else:
                # example: 8-player bracket:
                # we are in match 4, we need the winner of match 0 and 1
                # we are in match 5, we need the winner of match 2 and 3
                # we are in match 6, we need the winner of match 4 and 5
                match_base = 2 * (match_number - half_bracket)
                m.player_a_match = self.matches.get(play_order=match_base)
                m.player_b_match = self.matches.get(play_order=(match_base + 1))
            m.save()
            self.matches.add(m)
            self.save()

    def get_number_of_matches(self):
        if self.play_format == 0:
            return self.bracket_size() - 1
