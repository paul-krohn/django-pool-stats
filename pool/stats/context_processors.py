from .models import Season
from django.conf import settings


def season(request):
    try:
        _season = Season.objects.get(id=request.session['season_id'])
    # this exception used to be on KeyError, was the difference related to switch to postgres somehow?
    except Season.DoesNotExist:
        _season = Season.objects.get(is_default=True)
    return {
        'seasons': Season.objects.order_by('-pub_date')[0:4],
        'season': _season
    }


def league(request):
    return {
        'league': settings.LEAGUE,
    }
