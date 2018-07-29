from django.shortcuts import redirect, render, reverse

from ..models import Season
# from ..views.team import teams


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


def seasons(request):
    _seasons = Season.objects.all()
    context = {
        'seasons': _seasons
    }
    return render(request, 'stats/seasons.html', context)
