import datetime

from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache

from ..models import Week, ScoreSheet, Season
from ..views import check_season
from ..forms import ScoreSheetCreationForm


def week(request, week_id):
    _week = get_object_or_404(Week, id=week_id)

    official_matches = []
    unofficial_matches = []
    alternate_tables = []

    for a_match in _week.match_set.all():
        # an 'official' match has exactly one score sheet, which has been marked official;
        # also in the template, official matches are represented by their score sheet,
        # unofficial matches by the match
        match_score_sheets = ScoreSheet.objects.filter(match=a_match)
        if len(match_score_sheets.filter(official=True)) == 1:
            official_matches.append(match_score_sheets.filter(official=True)[0])
        else:
            unofficial_matches.append({
                'score_sheet_form': ScoreSheetCreationForm(instance=a_match),
                'score_sheets': match_score_sheets,
            })
            # some matches have alternate locations; the are separate so they can be called out in the template
            if a_match.alternate_table:
                alternate_tables.append(a_match)

    context = {
        'week': _week,
        'alternate_tables': alternate_tables,
        'unofficial_matches': unofficial_matches,
        'official_matches': official_matches
    }
    return render(request, 'stats/week.html', context)


def weeks(request):
    check_season(request)
    _season = Season.objects.get(id=request.session['season_id'])
    _weeks = Week.objects.filter(season=request.session['season_id']).order_by('date')
    context = {
        'weeks': _weeks,
        'season': _season
    }
    return render(request, 'stats/weeks.html', context)


@never_cache
def get_current_week(request, today_date=''):

    check_season(request)
    # now get the time range that is Sun-Sat this week; start with the DOW now
    today = datetime.date.today()
    if today_date != '':  # this param is really just here for tests.
        (year, month, day) = today_date.split('-')
        today = datetime.date(year=int(year), month=int(month), day=int(day))

    offset_days = today.weekday() % 6 + 1  # the number of days since Sunday.
    prev_sunday = today - datetime.timedelta(days=offset_days)
    next_saturday = prev_sunday + datetime.timedelta(days=6)

    season_weeks = Week.objects.filter(
        season_id=request.session['season_id'],
    ).order_by('date')
    closest_week = None
    if today <= season_weeks.first().date:
        closest_week = season_weeks.first()
    elif today >= season_weeks.last().date:
        closest_week = season_weeks.last()
    else:
        close_weeks = season_weeks.filter(
            date__lt=next_saturday,
            date__gt=prev_sunday,
        )
        if len(close_weeks) == 1:
            closest_week = close_weeks[0]
        elif len(close_weeks) == 2:
            closest_week = close_weeks[0]
            closest_week_gap = abs(today - close_weeks[0].date)
            for close_week in close_weeks:
                if abs(today - close_week.date) < closest_week_gap:
                    closest_week_gap = abs(close_week.date - today)
                    closest_week = close_week
    if closest_week:
        return redirect('week', week_id=closest_week.id)
    else:
        return redirect('weeks')
