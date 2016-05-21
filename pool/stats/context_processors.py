from .models import Season


def season(request):
    try:
        _season = Season.objects.get(id=request.session['season_id'])
    except KeyError:
        _season = Season.objects.get(is_default=True)
    return {
        'seasons': Season.objects.order_by('-pub_date')[0:4],
        'season': _season
    }
