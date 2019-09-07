import datetime

from django.db.models import Q
from django.shortcuts import redirect, render, get_object_or_404
from django.template import loader

from ..models import Team, Tie, TieBreakerResult, Season, PlayerSeasonSummary, ScoreSheet, Match
from ..utils import page_cache as cache
from ..views import check_season


def teams(request, season_id=None):
    check_season(request)
    if season_id is None:
        return redirect('teams', season_id=request.session['season_id'])
    team_list = Team.objects.filter(season=season_id).order_by('-win_percentage')
    season = Season.objects.get(id=request.session['season_id'])
    ties = Tie.objects.filter(season=season)
    tiebreakers = TieBreakerResult.objects.filter(tie__in=ties)
    context = {
        'teams': team_list,
        'season': season,
        'tiebreakers': tiebreakers,
    }
    return render(request, 'stats/teams.html', context)


def team(request, team_id, after=None):

    check_season(request)

    _team = get_object_or_404(Team, id=team_id)

    elo = request.session.get('elo', False)
    players_table_cache_key = '.'.join(['players_table', 'team', str(team_id), str(elo)])
    players_table = cache.get(players_table_cache_key)

    if not players_table:
        _players = PlayerSeasonSummary.objects.filter(
            player_id__in=list([x.id for x in _team.players.all()]),
            season_id=_team.season.id,
        ).order_by('player__last_name')

        template = loader.get_template('stats/player_table.html')

        players_table = template.render(request=request, context={
            'elo': elo,
            'players': _players,
            'show_teams': False,
        })
        cache.set(players_table_cache_key, players_table)


    official_score_sheets = ScoreSheet.objects.filter(official=True).filter(
        Q(match__away_team=_team) | Q(match__home_team=_team)
    ).order_by('match__week__date')
    unofficial_score_sheets = ScoreSheet.objects.filter(official=False).filter(
        Q(match__away_team=_team) | Q(match__home_team=_team)
    ).order_by('match__week__date')

    # we don't expect people to actually use the 'after' parameter, it is really to make test data
    # with long-ago dates usable .
    if after is not None:
        after_parts = list(map(int, after.split('-')))
        after_date = datetime.date(after_parts[0], after_parts[1], after_parts[2])
    else:
        after_date = datetime.date.today()
    after_date -= datetime.timedelta(days=2)
    _matches = Match.objects.filter(week__date__gt=after_date).filter(
        Q(away_team=_team) | Q(home_team=_team)
    ).order_by('week__date')

    _elo = request.session.get('elo', False)
    context = {
        'team': _team,
        'players_table': players_table,
        'official_score_sheets': official_score_sheets,
        'unofficial_score_sheets': unofficial_score_sheets,
        'matches': _matches,
    }
    return render(request, 'stats/team.html', context)
