from .models import Season
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist


def season(request):
    print('getting the season')
    try:
        _season = Season.objects.get(id=request.session['season_id'])
    except (ObjectDoesNotExist, KeyError):
        _season = Season.objects.get(is_default=True)
    return {
        'seasons': Season.objects.order_by('-pub_date')[0:4],
        'season': _season
    }


def league(request):
    return {
        'league': settings.LEAGUE,
    }
