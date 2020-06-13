from django.shortcuts import redirect, render

from ..models import Division, Team
from ..utils import page_cache as cache
from ..views.season import check_season_d


@check_season_d()
def divisions(request, season_id=None):

    divisions_cache_key = '.'.join(['divisions', str(season_id)])

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
        cache.set(divisions_cache_key, page)
    return page
