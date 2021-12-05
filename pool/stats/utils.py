import time

from django.core.cache import cache
from django.core.cache import caches
from django.utils.cache import get_cache_key

from .models import Season, PlayerSeasonSummary, Team
from .models.player_rating import rate_games


page_cache = caches['page']


def session_uid(request):
    if 'uid' not in request.session.keys():
        request.session['uid'] = str(hash(time.time()))[0:15]
    return request.session['uid']


def is_stats_master(user):
    return user.groups.filter(name='statsmaster').exists()


def expire_page(request, path=None, query_string=None, method='GET'):
    """
    :param request: "real" request, or at least one providing the same scheme, host, and port as what you want to expire
    :param path: The path you want to expire, if not the path on the request
    :param query_string: The query string you want to expire, as opposed to the path on the request
    :param method: the HTTP method for the page, if not GET
    :return: None
    """
    if query_string is not None:
        request.META['QUERY_STRING'] = query_string
    if path is not None:
        request.path = path
    request.method = method

    # get_raw_uri and method show, as of this writing, everything used in the cache key
    # print('req uri: {} method: {}'.format(request.get_raw_uri(), request.method))
    key = get_cache_key(request)
    if key in cache:
        cache.delete(key)


def update_season_stats(season_id):
    for team in Season.objects.get(id=season_id).team_set.all():
        team.count_games()
    rate_games()
    PlayerSeasonSummary.update_all(season_id=season_id)
    Team.update_rankings(season_id=season_id)


def expire_caches():
    page_cache.clear()


def get_dupes_from_dict(dictionary):
    return ['{}'.format(p) for p in {k: v for k, v in dictionary.items() if v > 1}]
