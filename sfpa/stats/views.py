import time

from django.shortcuts import render, redirect
from .models import Division, AwayLineupEntry, Game, GameOrder, HomeLineupEntry, Match, Player, \
    ScoreSheet, Season, Sponsor, Team, Week
from .models import PlayPosition
from .models import AwayPlayer, HomePlayer, PlayerSeasonSummary
from .models import AwaySubstitution, HomeSubstitution
from .forms import PlayerForm, ScoreSheetGameForm, DisabledScoreSheetGameForm
from django.forms import modelformset_factory

import django.forms
import django.db.models

from django.core.exceptions import ObjectDoesNotExist


def session_uid(request):
    if 'uid' not in request.session.keys():
        request.session['uid'] = str(hash(time.time()))[0:15]
    return request.session['uid']


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
    team_list = Team.objects.filter(season=request.session['season_id']).order_by('-win_percentage')
    season = Season.objects.get(id=request.session['season_id'])
    context = {
        'teams': team_list,
        'season': season,
    }
    return render(request, 'stats/teams.html', context)


def player(request, player_id):
    check_season(request)
    _player = Player.objects.get(id=player_id)
    summaries = PlayerSeasonSummary.objects.filter(player__exact=_player).order_by('-season')

    _score_sheets = ScoreSheet.objects.filter(official=True)

    # the set() is necessary to remove the dupes apparently created by the or clause
    _score_sheets = set(_score_sheets.filter(
        django.db.models.Q(away_lineup__player=_player)
        |
        django.db.models.Q(home_lineup__player=_player)
    ))

    context = {
        'score_sheets': _score_sheets,
        'summaries': summaries,
        'player': _player
    }
    return render(request, 'stats/player.html', context)


def players(request):
    check_season(request)
    _players = PlayerSeasonSummary.objects.filter(
        season=request.session['season_id']).order_by('-win_percentage', '-wins')

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


def update_players_stats(request):
    check_season(request)
    team_list = Team.objects.filter(season=request.session['season_id'])
    for a_team in team_list:
        away_score_sheets = ScoreSheet.objects.filter(match__away_team__exact=a_team, official__exact=True)
        home_score_sheets = ScoreSheet.objects.filter(match__home_team__exact=a_team, official__exact=True)
        for team_player in a_team.players.all():
            try:
                team_player_summary = PlayerSeasonSummary.objects.get(player__exact=team_player)
            except ObjectDoesNotExist:
                team_player_summary = PlayerSeasonSummary(player=team_player, season_id=request.session['season_id'])
            team_player_summary.wins = 0
            team_player_summary.losses = 0
            team_player_summary.four_ohs = 0
            team_player_summary.table_runs = 0

            for away_score_sheet in away_score_sheets:
                score_sheet_wins = len(
                    away_score_sheet.games.filter(
                        away_player__exact=team_player, winner='away'
                    ).exclude(home_player__exact=None)
                )
                if score_sheet_wins == 4:  # TODO: fix hard-coding of sweep win number
                    team_player_summary.four_ohs += 1
                team_player_summary.wins += score_sheet_wins
                team_player_summary.table_runs += len(away_score_sheet.games.filter(
                    away_player__exact=team_player, winner='away', table_run=True))
                team_player_summary.losses += len(away_score_sheet.games.filter(
                    away_player__exact=team_player, winner='home'))

            for home_score_sheet in home_score_sheets:
                score_sheet_wins = len(
                    home_score_sheet.games.filter(
                        home_player__exact=team_player, winner='home'
                    ).exclude(away_player__exact=None)
                )
                if score_sheet_wins == 4:  # TODO: fix hard-coding of sweep win number
                    team_player_summary.four_ohs += 1
                team_player_summary.wins += score_sheet_wins
                team_player_summary.table_runs += len(home_score_sheet.games.filter(
                    home_player__exact=team_player, winner='home', table_run=True))
                team_player_summary.losses += len(home_score_sheet.games.filter(
                    home_player__exact=team_player, winner='away'))
            denominator = team_player_summary.losses + team_player_summary.wins
            if denominator > 0:
                team_player_summary.win_percentage = team_player_summary.wins / denominator

            team_player_summary.save()
    return redirect('/stats/players')


def team(request, team_id):

    _team = Team.objects.get(id=team_id)
    _players = PlayerSeasonSummary.objects.filter(player_id__in=list([x.id for x in _team.players.all()]))

    context = {
        'team': _team,
        'players': _players
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

    official_matches = []
    unofficial_matches = []

    for a_match in _week.match_set.all():
        # an 'official' match has exactly one score sheet, which has been marked official;
        # also in the template, official matches are represented by their score sheet,
        # unofficial matches by the match
        match_score_sheets = ScoreSheet.objects.filter(match=a_match)
        if len(match_score_sheets.filter(official=True)) == 1:
            official_matches.append(match_score_sheets.filter(official=True)[0])
        else:
            print('oh yes and the len() thing worked out to {}'.format(match_score_sheets.filter(official=True)))
            unofficial_matches.append(a_match)

    print('hey there are some matches in week {}'.format(_week))
    print('official matches (score sheets really): {}'.format(official_matches))
    print('unofficial matches (score sheets really): {}'.format(unofficial_matches))

    context = {
        'week': _week,
        'unofficial_matches': unofficial_matches,
        'official_matches': official_matches
    }
    return render(request, 'stats/week.html', context)


def weeks(request):
    check_season(request)
    _season = Season.objects.get(id=request.session['season_id'])
    _weeks = Week.objects.filter(season=request.session['season_id'])
    context = {
        'weeks': _weeks,
        'season': _season
    }
    return render(request, 'stats/weeks.html', context)


def match(request, match_id):
    _match = Match.objects.get(id=match_id)
    match_score_sheets = ScoreSheet.objects.filter(match_id__exact=_match.id, official=True)

    score_sheet_game_formsets = None

    if len(match_score_sheets):
        score_sheet_game_formset_f = modelformset_factory(
            model=Game,
            form=DisabledScoreSheetGameForm,
            max_num=len(match_score_sheets[0].games.all())
        )
        score_sheet_game_formsets = []
        for a_score_sheet in match_score_sheets:
            score_sheet_game_formsets.append(
                score_sheet_game_formset_f(
                    queryset=a_score_sheet.games.all(),
                )
            )
    context = {
        'match': _match,
        'score_sheets': score_sheet_game_formsets
    }
    return render(request, 'stats/match.html', context)


def score_sheets(request):
    sheets = ScoreSheet.objects.filter(official=False)

    sheets_with_scores = []
    for sheet in sheets:
        sheets_with_scores.append({
            'sheet': sheet,
        })

    context = {
        'score_sheets': sheets_with_scores
    }
    return render(request, 'stats/score_sheets.html', context)


def player_score_sheet_summary(games, a_player):

    away_wins = games.filter(winner='away', away_player=a_player)
    away_losses = games.filter(winner='home', away_player=a_player)

    home_wins = games.filter(winner='home', home_player=a_player)
    home_losses = games.filter(winner='away', home_player=a_player)

    return {
        'wins': len(away_wins.all()) + len(home_wins.all()),
        'losses': len(away_losses.all()) + len(home_losses.all()),
        'table_runs': len(away_wins.filter(table_run=True)) + len(home_wins.filter(table_run=True)),
    }


def get_score_sheet_player_summaries(a_score_sheet, away_home):

    player_score_sheet_summaries = []
    if away_home == 'away':
        lineup_entries = a_score_sheet.away_lineup.all()
    else:
        lineup_entries = a_score_sheet.home_lineup.all()
    for lineup_entry in lineup_entries:
        if lineup_entry.player is None:
            continue
        summary = {
            'player': lineup_entry.player,
        }
        summary.update(player_score_sheet_summary(
            games=a_score_sheet.games.filter(forfeit=False),
            a_player=lineup_entry.player
        ))
        player_score_sheet_summaries.append(summary)
    return player_score_sheet_summaries


def score_sheet(request, score_sheet_id):
    s = ScoreSheet.objects.get(id=score_sheet_id)
    score_sheet_game_formset_f = modelformset_factory(
        Game,
        form=DisabledScoreSheetGameForm,
        max_num=len(s.games.all()),
    )
    score_sheet_game_formset = score_sheet_game_formset_f(
        queryset=s.games.all(),
    )

    context = {
        'score_sheet': s,
        'games_formset': score_sheet_game_formset,
        'away_player_score_sheet_summaries': get_score_sheet_player_summaries(s, 'away'),
        'home_player_score_sheet_summaries': get_score_sheet_player_summaries(s, 'home')
    }
    return render(request, 'stats/score_sheet.html', context)


def score_sheet_edit(request, score_sheet_id):
    s = ScoreSheet.objects.get(id=score_sheet_id)
    if session_uid(request) != s.creator_session:
        if not request.user.is_superuser:
            return redirect('score_sheet', s.id)
    score_sheet_game_formset_f = modelformset_factory(
        Game,
        form=ScoreSheetGameForm,
        max_num=len(s.games.all())
    )
    if request.method == 'POST':
        score_sheet_game_formset = score_sheet_game_formset_f(
            request.POST, queryset=s.games.all()
        )
        if score_sheet_game_formset.is_valid():
            score_sheet_game_formset.save()
    else:
        score_sheet_game_formset = score_sheet_game_formset_f(
            queryset=s.games.all(),
        )
    context = {
        'score_sheet': s,
        'games_formset': score_sheet_game_formset,
    }
    return render(request, 'stats/score_sheet_edit.html', context)


def score_sheet_create(request, match_id):
    # m = Match.objects.get(id=match_id)
    s = ScoreSheet(match=Match.objects.get(id=match_id))
    s.creator_session = session_uid(request)
    s.save()
    s.initialize_lineup()
    s.initialize_games()

    return redirect('score_sheet_edit', score_sheet_id=s.id)


def score_sheet_lineup(request, score_sheet_id, away_home):
    s = ScoreSheet.objects.get(id=score_sheet_id)

    # it would be prettier to do this by passing kwargs but,
    # it seems you can't do that with a ModelForm so, the ugly is here.
    lineup_players_queryset = s.match.away_team.players.all()
    lineup_queryset = s.away_lineup.all()
    lineup_model = AwayLineupEntry
    if away_home == 'home':
        lineup_players_queryset = s.match.home_team.players.all()
        lineup_queryset = s.home_lineup.all()
        lineup_model = HomeLineupEntry

    class LineupForm(django.forms.ModelForm):
        # thanks to stack overflow for this, from here:
        # http://stackoverflow.com/questions/1982025/django-form-from-related-model
        player = django.forms.ModelChoiceField(
            queryset=lineup_players_queryset,
            required=False,
        )

    lineup_formset_f = modelformset_factory(
        model=lineup_model, fields=['player'], form=LineupForm,
        extra=0, max_num=len(PlayPosition.objects.all())
    )

    if request.method == 'POST':
        lineup_formset = lineup_formset_f(request.POST, queryset=lineup_queryset)
        if lineup_formset.is_valid():
            lineup_formset.save()
            s.set_games()
            return redirect('score_sheet_edit', score_sheet_id=s.id)
    else:
        lineup_formset = lineup_formset_f(queryset=lineup_queryset)

    context = {
        'score_sheet': s,
        'lineup_formset': lineup_formset,
        'away_home': away_home
    }
    return render(request, 'stats/score_sheet_lineup_edit.html', context)


def score_sheet_substitutions(request, score_sheet_id, away_home):
    s = ScoreSheet.objects.get(id=score_sheet_id)

    substitution_players_queryset = s.match.away_team.players.all()
    substitution_queryset = s.away_substitutions.all()
    substitution_model = AwaySubstitution
    add_substitution_function = s.away_substitutions.add
    if away_home == 'home':
        substitution_players_queryset = s.match.home_team.players.all()
        substitution_queryset = s.home_substitutions.all()
        substitution_model = HomeSubstitution
        add_substitution_function = s.home_substitutions.add

    class SubstitutionForm(django.forms.ModelForm):
        player = django.forms.ModelChoiceField(
            queryset=substitution_players_queryset,
            required=False,
        )

    substitution_formset_f = modelformset_factory(
        model=substitution_model,
        form=SubstitutionForm,
        fields=['game_order', 'player', 'play_position'],
        max_num=2
    )
    if request.method == 'POST':
        substitution_formset = substitution_formset_f(
            request.POST, queryset=substitution_queryset
        )
        if substitution_formset.is_valid():
            print('saving away subs for {}'.format(s.match))
            for substitution in substitution_formset.save():
                print('adding {} as {} in game {}'.format(
                    substitution.player, substitution.play_position, substitution.game_order))
                add_substitution_function(substitution)
            set_games_for_score_sheet(s.id)
            return redirect('score_sheet_edit', score_sheet_id=s.id)
    else:
        substitution_formset = substitution_formset_f(queryset=substitution_queryset)
        context = {
            'score_sheet': s,
            'substitutions_form': substitution_formset,
            'away_home': away_home,
        }
        return render(request, 'stats/score_sheet_substitutions.html', context)


def update_teams_stats(request):
    # be sure about what season we are working on
    check_season(request)
    Team.update_teams_stats(season_id=request.session['season_id'])
    return redirect('teams')


def unofficial_results(request):
    sheets = ScoreSheet.objects.filter(official=False)

    context = {
        'score_sheets': sheets,
    }

    return render(request, 'stats/unofficial_results.html', context)
