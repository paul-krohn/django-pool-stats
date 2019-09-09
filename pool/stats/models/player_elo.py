from elo import Rating, setup as elo_setup

from django.db import models

from .game import Game
from .player import Player
from .playersummary import PlayerSeasonSummary
from .season import Season

from .globals import away_home


class PlayerElo(models.Model):
    player = models.ForeignKey(Player,
       on_delete=models.CASCADE,
    )
    rating = models.FloatField(
        null=True,
        blank=True,
    )
    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE
    )

    rater = elo_setup(initial=1200, beta=80)

    @classmethod
    def get_season_rateable_games(cls, season_id):

        main_filter_args = {
            'scoresheet__official': True,
            'scoresheet__match__playoff': False,
            'scoresheet__match__season_id': season_id,
            'playerelo__isnull': True,
            'forfeit': False,
        }

        games = Game.objects.filter(
            **main_filter_args
        ).exclude(
            winner=''
        ).exclude(
            winner=None
        ).exclude(
            away_player=None
        ).exclude(
            home_player=None
        ).order_by('scoresheet__match__week__date', 'order')

        return games

    @classmethod
    def update_season(cls, season_id):
        games = cls.get_season_rateable_games(season_id)
        print('there are {} games to rate in season {}'.format(len(games), season_id))
        for game in games:
            cls.update_from_game(game, season_id)

    @classmethod
    def update_from_game(cls, game, season_id):  # summaries, winner_index, loser_index):

        wl = ['winner', 'loser']
        summaries = get_summaries(game, season_id)
        winner = game.winner

        # if the winner is 'home'
        winner_index = away_home.index(winner)
        loser_index = 1 - away_home.index(winner)

        new_elos = dict()
        new_elos['winner'], new_elos['loser'] = cls.rater.rate_1vs1(
            cls.rater.create_rating(get_old_elo(summaries[away_home[winner_index]])),
            cls.rater.create_rating(get_old_elo(summaries[away_home[loser_index]])),
        )
        # logger.debug(
        #     "new elos: {}/{} and {}/{}".format(
        #         game.away_player,
        #         new_elos[wl[winner_index]],
        #         game.home_player,
        #         new_elos[wl[loser_index]],
        #     )
        # )
        PlayerElo(
            rating=new_elos[wl[winner_index]],
            player=game.away_player,
            game=game,
        ).save()
        PlayerElo(
            rating=new_elos[wl[loser_index]],
            player=game.home_player,
            game=game,
        ).save()

        summaries[away_home[winner_index]].elo = new_elos['winner']
        summaries[away_home[loser_index]].elo = new_elos['loser']

        summaries[away_home[winner_index]].save()
        summaries[away_home[loser_index]].save()


def get_summaries(game, season_id):
    summaries = dict()
    for ah in away_home:
        player = getattr(game, '{}_player'.format(ah))
        try:
            summaries[ah] = PlayerSeasonSummary.objects.get(
                season_id=season_id, player=player
            )
        except PlayerSeasonSummary.DoesNotExist as e:
            print(
                "no season summary for {}({}) based on game id {}. error: {}".format(player, player.id, game.id, e))
    return summaries


def get_games_filter(options):
    main_filter_args = {
        'scoresheet__official': True,
        'scoresheet__match__playoff': False,
        'forfeit': False,
    }
    if options['type'] == 'scoresheet':
        main_filter_args['scoresheet__id'] = options['the_id']
    elif options['type'] == 'season':
        main_filter_args['scoresheet__match__season_id'] = options['the_id']
    return main_filter_args


def get_previous_season(season_id):
    this_season = Season.objects.get(id=season_id)
    # now get the seasons before this one (ie excluding this one), ordered by date
    seasons = Season.objects.filter(pub_date__lt=this_season.pub_date).order_by('-pub_date')
    return seasons[0] or None


def get_old_elo(player_summary):

    # if the previous season is None, and there is no elo, return a new/default elo
    previous_elo = None
    if player_summary.elo is not None:
        previous_elo = player_summary.elo
    else:
        previous_season = get_previous_season(player_summary.season_id)
        if previous_season is not None:
            previous_season_summary = PlayerSeasonSummary.objects.filter(
                player=player_summary.player, season=previous_season
            )
            if len(previous_season_summary):
                previous_elo = previous_season_summary[0].elo
                print("previous elo for {} ({}): {}".format(
                    previous_season_summary[0], previous_season_summary[0].player.id, previous_elo
                ))
    return Rating(previous_elo)


