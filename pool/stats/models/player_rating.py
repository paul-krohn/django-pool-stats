from django.db import models

from .game import Game
from .player import Player

from .singleton import SingletonModel

from trueskill import TrueSkill, Rating, rate_1vs1


DEFAULT_MU = 1000
DEFAULT_SIGMA = 333
DEFAULT_BETA = 200

trueskill_env = TrueSkill(
    draw_probability=0.00,
    mu=DEFAULT_MU,
    sigma=DEFAULT_SIGMA,
    beta=DEFAULT_BETA,
)

trueskill_env.make_as_global()


class PlayerRatingException(Exception):
    pass


def check_unofficial_games():
    unofficial_games = Game.objects.filter(
        models.Q(scoresheet__official=False)
    ).filter(
        forfeit=False
    )
    if len(unofficial_games) == 0:
        return True
    else:
        raise PlayerRatingException("There are {} unofficial games; rating of players cannot proceed".format(
            len(unofficial_games)
        ))


def get_current_rating(player_id):
    player_rating = PlayerRating.objects.filter(player_id=player_id).order_by('game_id').last()
    if player_rating is None:
        return Rating()
    else:
        return Rating(mu=player_rating.mu, sigma=player_rating.sigma)


def get_initial_game():
    return Game.objects.filter(scoresheet__official=True).order_by('id').first()


def check_bookmark_initialized():
    if not len(PlayerRatingBookmark.objects.all()):
        PlayerRatingBookmark(game=get_initial_game()).save()


def get_unrated_games():

    last_rated_game = PlayerRatingBookmark.objects.all()[0].game
    games = Game.objects.filter(
        models.Q(scoresheet__official=True)
    ).filter(
        forfeit=False
    ).filter(
        id__gt=last_rated_game.id
    ).filter(
        away_player__isnull=False
    ).filter(
        home_player__isnull=False
    ).exclude(
        winner=None,
    ).exclude(
        winner='',
    ).order_by('id')

    return games


def rate_game(game):
    try:
        away_rating = get_current_rating(game.away_player_id)
        home_rating = get_current_rating(game.home_player_id)
        if game.winner == 'away':
            new_away_rating, new_home_rating = rate_1vs1(away_rating, home_rating)
        else:
            new_home_rating, new_away_rating = rate_1vs1(home_rating, away_rating)

        PlayerRating(game=game, player=game.away_player, mu=new_away_rating.mu, sigma=new_away_rating.sigma).save()
        PlayerRating(game=game, player=game.home_player, mu=new_home_rating.mu, sigma=new_home_rating.sigma).save()
    except Exception as e:
        print("failed rating game between {} and {}".format(game.away_player, game.home_player))


def rate_games():
    # check_unofficial_games()
    check_bookmark_initialized()
    unrated_games = get_unrated_games()
    for game in unrated_games:
        rate_game(game)
        update_bookmark(game)


def update_bookmark(game):
    bookmark = PlayerRatingBookmark.objects.get(id=1)
    bookmark.game = game
    bookmark.save()


class PlayerRatingBookmark(SingletonModel):

    game = models.ForeignKey(Game, on_delete=models.CASCADE)


class PlayerRating(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    mu = models.FloatField(
        default=DEFAULT_MU,
    )
    sigma = models.FloatField(
        default=DEFAULT_SIGMA,
    )
    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE
    )
