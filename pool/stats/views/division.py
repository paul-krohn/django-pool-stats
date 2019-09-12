from django.shortcuts import redirect, render

from ..models import Division, Team
from ..utils import page_cache as cache
from ..views import check_season


def divisions(request, season_id=None):
    check_season(request)
    if season_id is None:
        return redirect('divisions', season_id=request.session['season_id'])

    divisions_cache_key = '.'.join([
        'divisions',
        season_id
    ])

    page = cache.get(divisions_cache_key)
    if not page:
        _divisions = Division.objects.filter(season=request.session['season_id']).order_by('name')
        # this wrapper divisions dodge is needed so the teams within each division
        # can be sorted by ranking
        wrapper_divisions = []
        for _division in _divisions:
            _teams = Team.objects.filter(
                division=_division,
                season=request.session['season_id']
            ).order_by('ranking')
            wrapper_divisions.append({
                'division': _division,
                'teams': _teams
            })
        context = {
            'divisions': _divisions,
            'wrapper_divisions': wrapper_divisions

        }
        page = render(request, 'stats/divisions.html', context)
        cache.setb(divisions_cache_key, page)
    return page
