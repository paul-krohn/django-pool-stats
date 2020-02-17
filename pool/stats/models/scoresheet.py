from django.db import models

from .game import Game, GameOrder
from .match import Match
from .lineup import AwayLineupEntry, HomeLineupEntry, AwaySubstitution, HomeSubstitution
from .player import AwayPlayer, HomePlayer
from .playposition import PlayPosition

from .globals import away_home, logger


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

    def forfeit_wins(self, ah):
        return len(self.games.filter(winner=ah).filter(forfeit=True))

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
        for ah in away_home:
            list_subs = getattr(self, '{}_substitutions'.format(ah))
            for substitution in list_subs.all():
                position_m = getattr(substitution.game_order, '{}_position'.format(ah))
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

    # def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
    #     super(ScoreSheet, self).save(*args, **kwargs)
    #
    def copy(self, session_id):
        """

        :param session_id:
        :return: new scoresheet id
        """

        old_ss = self

        new_ss = ScoreSheet(
            match=old_ss.match,
            comment=old_ss.comment,
            creator_session=session_id,
        )
        new_ss.save()

        for ah in away_home:
            lineup_entries = getattr(self, '{}_lineup'.format(ah))
            new_lineup = getattr(new_ss, '{}_lineup'.format(ah))
            for lineup_entry in lineup_entries.all():
                le = eval('{}LineupEntry'.format(ah.capitalize()))(
                    player=lineup_entry.player,
                    position=lineup_entry.position,
                )
                le.save()
                new_lineup.add(le)
            old_substitutions = getattr(self, '{}_substitutions'.format(ah))
            new_subs = getattr(new_ss, '{}_substitutions'.format(ah))
            for old_substitution in old_substitutions.all():
                new_sub = eval('{}Substitution'.format(ah.capitalize()))(
                    game_order=old_substitution.game_order,
                    player=old_substitution.player,
                    play_position=old_substitution.play_position,
                )
                new_sub.save()
                new_subs.add(new_sub)

        for old_game in old_ss.games.all():
            new_game = Game(
                away_player=old_game.away_player,
                home_player=old_game.home_player,
                winner=old_game.winner,
                order=old_game.order,
                table_run=old_game.table_run,
                forfeit=old_game.forfeit,
                timestamp=old_game.timestamp,
            )
            new_game.save()
            new_ss.games.add(new_game)

        new_ss.save()
        return new_ss.id

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

    def player_summaries(self, away_home, as_dict=False):

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
                'player': player.as_dict() if as_dict else player,
            }
            summary.update(self.player_summary(
                a_player=player
            ))
            player_score_sheet_summaries.append(summary)
        return player_score_sheet_summaries

    def summary(self):
        _summary = {}
        for ah in away_home:
            _summary.update({ah: getattr(self.match, '{}_team'.format(ah)).as_dict()})
            _summary[ah].update({'players': self.player_summaries(ah, True)})
            _summary[ah].update({'wins': getattr(self, '{}_wins'.format(ah))()})

        return {'teams': _summary, 'issues': self.self_check()}

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

        self.complete = True
        if len(issues):
            if mark_for_review:
                self.status = 2  # needs changes
            self.complete = False
        self.save()
        return issues
