from .models import Season


def season(request):
    return {
        'seasons': Season.objects.order_by('-pub_date')[0:4],
        'season': Season.objects.get(id=request.session['season_id'])
    }
