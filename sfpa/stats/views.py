from django.shortcuts import render, redirect
from .models import Division, AwayLineupEntry, Game, GameOrder, HomeLineupEntry, Match, Player, PlayPosition, ScoreSheet, Season, Sponsor, Team, Week
from .forms import PlayerForm
from django.forms import modelformset_factory


def set_season(request, season_id=None):
    """
    Allow the user to set their season to a value other than the default.
    :param request:
    :return: bool
    """
    if season_id is None:
        season_id = Season.objects.get(is_default=True).id
    request.session['season_id'] = season_id
    request.session.save()
    # hard-coded urls are bad okay?
    return redirect(to='/stats/')


def check_season(request):
    if 'season_id' in request.session:
        return
    else:
        set_season(request)


def index(request):
    check_season(request)
    team_list = Team.objects.filter(season=request.session['season_id'])
    season = Season.objects.get(id=request.session['season_id'])
    context = {
        'teams': team_list,
        'season': season,
    }
    return render(request, 'stats/teams.html', context)


def player(request, player_id):
    _player = Player.objects.get(id=player_id)
    context = {
        'player': _player
    }
    return render(request, 'stats/player.html', context)


def players(request):
    #  filter on membership in a team in the current season
    check_season(request)
    _players = Player.objects.filter(team__season=request.session['season_id'])
    context = {
        'players': _players
    }
    return render(request, 'stats/players.html', context)


def player_create(request):
    if request.method == 'POST':
        player_form = PlayerForm(request.POST)
        if player_form.is_valid():
            p = Player()
            print(player_form.cleaned_data['team'])
            t = player_form.cleaned_data['team']
            if player_form.cleaned_data['display_name'] is not '':
                p.display_name = player_form.cleaned_data['display_name']
            p.first_name = player_form.cleaned_data['first_name']
            p.last_name = player_form.cleaned_data['last_name']
            p.save()
            t.players.add(p)
            return redirect('team', t.id)
    else:
        player_form = PlayerForm()
    context = {
        'form': player_form
    }
    return render(request, 'stats/player_create.html', context)


def team(request, team_id):

    _team = Team.objects.get(id=team_id)
    context = {
        'team': _team
    }
    return render(request, 'stats/team.html', context)


def seasons(request):
    _seasons = Season.objects.all()
    context = {
        'seasons': _seasons
    }
    return render(request, 'stats/seasons.html', context)


def sponsor(request, sponsor_id):
    _sponsor = Sponsor.objects.get(id=sponsor_id)
    context = {
        'sponsor': _sponsor
    }
    return render(request, 'stats/sponsor.html', context)


def sponsors(request):
    _sponsors = Sponsor.objects.all()
    context = {
        'sponsors': _sponsors
    }
    return render(request, 'stats/sponsors.html', context)


def divisions(request):
    check_season(request)
    _divisions = Division.objects.filter(season=request.session['season_id'])
    context = {
        'divisions': _divisions
    }
    return render(request, 'stats/divisions.html', context)


def week(request, week_id):
    _week = Week.objects.get(id=week_id)
    context = {
        'week': _week
    }
    return render(request, 'stats/week.html', context)


def weeks(request):
    check_season(request)
    _weeks = Week.objects.filter(season=request.session['season_id'])
    context = {
        'weeks': _weeks
    }
    return render(request, 'stats/weeks.html', context)


def match(request, match_id):
    _match = Match.objects.get(id=match_id)
    context = {
        'match': _match
    }
    return render(request, 'stats/match.html', context)


def matches(request):
    _matches = Match.objects.filter(season=request.session['season_id'])
    context = {
        'matches': _matches
    }
    return render(request, 'stats/matches.html', context)


def score_sheets(request):
    pass


def score_sheet(request, score_sheet_id):
    s = ScoreSheet.objects.get(id=score_sheet_id)

    context = {}
    return render(request, 'stats/score_sheet.html', context)


def score_sheet_edit(request, score_sheet_id):
    s = ScoreSheet.objects.get(id=score_sheet_id)

    context = {
        'score_sheet': s
    }
    return render(request, 'stats/score_sheet_edit.html', context)


def score_sheet_create(request, match_id):
    m = Match.objects.get(id=match_id)
    s = ScoreSheet(match=m)
    s.save()
    for lineup_position in PlayPosition.objects.all():
        ale = AwayLineupEntry(position=lineup_position)
        ale.save()
        hle = HomeLineupEntry(position=lineup_position)
        hle.save()
        s.away_lineup.add(ale)
        s.home_lineup.add(hle)
    s.save()

    # now create games, per the game order table
    for g in GameOrder.objects.all():
        game = Game()
        game.table_run = False
        game.forfeit = False
        game.save()
        s.games.add(game)
    s.save()

    return redirect('score_sheet_edit', score_sheet_id=s.id)


def score_sheet_away_lineup(request, score_sheet_id):
    s = ScoreSheet.objects.get(id=score_sheet_id)
    away_lineup_formset_f = modelformset_factory(
        # '6' really ought to be 'len(something)'
        model=AwayLineupEntry, exclude=[], extra=0, max_num=6
    )
    if request.method == 'POST':
        away_lineup_formset = away_lineup_formset_f(request.POST, queryset=s.away_lineup.all())
        if away_lineup_formset.is_valid():
            away_lineup_formset.save()
    else:
        # this way, we get the right number of forms, with the right position choices,
        # but with *every* player listed
        away_lineup_formset = away_lineup_formset_f(queryset=s.away_lineup.all())

    context = {
        'score_sheet': s,
        'away_form': away_lineup_formset,
    }
    return render(request, 'stats/lineup_edit.html', context)


def lineup_edit(request, lineup_id):
    pass


def lineup_create(request, scoresheet):
    pass


