from functools import wraps

from django.shortcuts import redirect, render, reverse

from ..models import Season


def get_default_season():
    default_season_id = 0
    try:
        default_season_id = Season.objects.get(is_default=True).id
    except Season.DoesNotExist as e:
        # there is no default season, try to get the last/latest one; get them in descending order, as
        # negative indexing does not work on querysets.
        the_seasons = Season.objects.order_by('-pub_date')
        if len(the_seasons):
            default_season_id = the_seasons[0].id
    return default_season_id


def set_season(request, season_id=None):
    """
    Allow the user to set their season to a value other than the default.
    :param request:
    :param season_id: the season to use, if not the current default
    :return: bool
    """
    if season_id is None:
        season_id = get_default_season()
    request.session['season_id'] = season_id
    request.session.save()
    # hard-coded urls are bad okay?
    redirect_to = '/stats/'
    if season_id:
        redirect_to = reverse('teams', kwargs={'season_id': season_id})
    return redirect(redirect_to)


def check_season(request):
    if 'season_id' not in request.session:
        request.session['season_id'] = get_default_season()
        request.session.save()


class check_season_d(object):

    def __init__(self, do_redirect):
        print("we are in init, do_redirect is {}".format(do_redirect))
        self.do_redirect = do_redirect
        pass

    def __call__(self, func):

        print("we are in call, function is {}".format(func))

        def wr(*args, **kwargs):
            print("inside wr, do_redirect is {}".format(self.do_redirect))
            return func(*args, **kwargs)
            # print("after calling func")
        return wr


def check_season_dec(func, *do_redirect):

    redirect_url = '/stats/seasons/'

    @wraps(func)
    def _inner(request, *args, **kwargs):
        # print("decorator called")
        url_season_id = int(kwargs.get('season_id', 0))
        session_season_id = request.session.get('season_id', 0)

        if session_season_id == 0:
            default_season = get_default_season()
            if default_season != 0:
                request.session['season_id'] = default_season
                request.session.save()

        season_id = url_season_id or request.session.get('season_id')
        if season_id == 0:
            return redirect(redirect_url)
        else:
            if do_redirect:
                kwargs.update({'season_id': season_id})
            return func(request, *args, **kwargs)

    return _inner


def check_season_dec_no_redir(func):
    return check_season_dec(func, do_redirect=False)


def seasons(request):
    _seasons = Season.objects.all()
    context = {
        'seasons': _seasons
    }
    return render(request, 'stats/seasons.html', context)
