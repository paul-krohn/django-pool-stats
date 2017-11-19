import time

from django.shortcuts import render, redirect, get_object_or_404
from .models import Division, AwayLineupEntry, Game, HomeLineupEntry, Match, Player, \
    ScoreSheet, Season, Sponsor, Team, Week
from .models import PlayPosition
from .models import PlayerSeasonSummary
from .models import AwaySubstitution, HomeSubstitution
from .forms import PlayerForm, ScoreSheetGameForm, DisabledScoreSheetGameForm, ScoreSheetCompletionForm
from .forms import LineupFormSet
from django.forms import modelformset_factory

import django.forms
import django.db.models
from django.conf import settings
from django.core.cache import cache

import logging
logger = logging.getLogger(__name__)


def session_uid(request):
    if 'uid' not in request.session.keys():
        request.session['uid'] = str(hash(time.time()))[0:15]
    return request.session['uid']


def set_season(request, season_id=None):
    """
    Allow the user to set their season to a value other than the default.
    :param request:
    :param season_id: the season to use, if not the current default
    :return: bool
    """
    if season_id is None:
        season_id = Season.objects.get(is_default=True).id
    request.session['season_id'] = season_id
    request.session.save()
    # hard-coded urls are bad okay?
    return redirect(request.META.get('HTTP_REFERER', '/stats/'))


def user_can_edit_scoresheet(request, score_sheet_id):

    s = ScoreSheet.objects.get(id=score_sheet_id)
    # you can edit a score sheet if it is not official and either you created it,
    # or you are an admin
    if (not s.official) and ((session_uid(request) == s.creator_session) or request.user.is_superuser):
        return True
    else:
        return False


def check_season(request):
    if 'season_id' in request.session:
        return
    else:
        set_season(request)


def get_player_rankings_view_cache_key(request):
    try:
        request.session['season_id']
    except KeyError:
        check_season(request)
    return 'player_{}'.format(request.session['season_id'])


def get_single_player_view_cache_key(season_id, player_id):
    return 'season_{}_player_{}'.format(season_id, player_id)


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
    cache_key = get_single_player_view_cache_key(request.session['season_id'], player_id)
    cached_content = cache.get(cache_key)
    if cached_content is None:
        _player = get_object_or_404(Player, id=player_id)
        summaries = PlayerSeasonSummary.objects.filter(player__exact=_player).order_by('-season')
        _score_sheets_with_dupes = ScoreSheet.objects.filter(official=True).filter(
            django.db.models.Q(away_lineup__player=_player) | django.db.models.Q(home_lineup__player=_player)
            |
            django.db.models.Q(away_substitutions__player=_player) | django.db.models.Q(home_substitutions__player=_player)
        ).order_by('match__week__date').filter(match__week__season=request.session['season_id'])
        # there are dupes in _score_sheets at this point, so we have to remove them; method is cribbed from:
        # http://stackoverflow.com/questions/480214/how-do-you-remove-duplicates-from-a-list-in-python-whilst-preserving-order
        seen = set()
        seen_add = seen.add
        _score_sheets = [x for x in _score_sheets_with_dupes if not (x in seen or seen_add(x))]
        context = {
            'score_sheets': _score_sheets,
            'summaries': summaries,
            'player': _player,
        }
        cached_content = render(request, 'stats/player.html', context)
        cache.set(cache_key, cached_content)
    return cached_content


def players(request):
    # in this view, the standard/decorator caching does not work well; as the players vary by
    # season, which is not in the URL; so use the cache API directly.

    check_season(request)
    # players_view_key = 'players_{}'.format(request.session['season_id'])
    _players = PlayerSeasonSummary.objects.filter(
        season=request.session['season_id'],
        ranking__gt=0
    ).order_by('-win_percentage', '-wins')

    cache_key = get_player_rankings_view_cache_key(request)

    context = {
        'players': _players,
        'show_teams': True,  # referenced in the player_table.html template
        'cache_key': cache_key,
    }
    view = render(request, 'stats/players.html', context)
    return view


def player_create(request):
    if request.method == 'POST':
        player_form = PlayerForm(request.POST)
        if player_form.is_valid():
            p = Player()
            logger.debug(player_form.cleaned_data['team'])
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

    PlayerSeasonSummary.update_all(season_id=request.session['season_id'])
    # delete the player view cache; then redirect to the players view, which
    # will repopulate the cache
    cache.delete(get_player_rankings_view_cache_key(request))
    return redirect('/stats/players')


def team(request, team_id):

    _team = get_object_or_404(Team, id=team_id)
    _players = PlayerSeasonSummary.objects.filter(
        player_id__in=list([x.id for x in _team.players.all()]),
    ).order_by('player__last_name')
    _score_sheets = set(ScoreSheet.objects.filter(official=True).filter(
        django.db.models.Q(match__away_team=_team) | django.db.models.Q(match__home_team=_team)
    ))

    context = {
        'team': _team,
        'players': _players,
        'show_players': False,
        'scoresheets': _score_sheets,
        'cache_key': _team,
    }
    return render(request, 'stats/team.html', context)


def seasons(request):
    _seasons = Season.objects.all()
    context = {
        'seasons': _seasons
    }
    return render(request, 'stats/seasons.html', context)


def sponsor(request, sponsor_id):
    _sponsor = get_object_or_404(Sponsor, id=sponsor_id)
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
    _divisions = Division.objects.filter(season=request.session['season_id']).order_by('name')
    # this wrapper divisions dodge is needed so the teams within each division
    # can be sorted by ranking
    wrapper_divisions = []
    for _division in _divisions:
        teams = Team.objects.filter(
            division=_division,
            season=request.session['season_id']
        ).order_by('ranking')
        wrapper_divisions.append({
            'division': _division,
            'teams': teams
        })
    context = {
        'divisions': _divisions,
        'wrapper_divisions': wrapper_divisions

    }
    return render(request, 'stats/divisions.html', context)


def week(request, week_id):
    _week = get_object_or_404(Week, id=week_id)

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
            unofficial_matches.append(a_match)

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
    _match = get_object_or_404(Match, id=match_id)
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


def score_sheet(request, score_sheet_id):
    s = get_object_or_404(ScoreSheet, id=score_sheet_id)
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
        'edit_link': user_can_edit_scoresheet(request, score_sheet_id),
        'games_formset': score_sheet_game_formset,
        'away_player_score_sheet_summaries': s.player_summaries('away'),
        'home_player_score_sheet_summaries': s.player_summaries('home')
    }
    return render(request, 'stats/score_sheet.html', context)


def score_sheet_complete(request, score_sheet_id):
    s = ScoreSheet.objects.get(id=score_sheet_id)
    score_sheet_game_formset_f = modelformset_factory(
        Game,
        form=DisabledScoreSheetGameForm,
        max_num=len(s.games.all()),
    )
    score_sheet_game_formset = score_sheet_game_formset_f(
        queryset=s.games.all(),
    )

    if request.method == 'POST':
        score_sheet_completion_form = ScoreSheetCompletionForm(request.POST, instance=s)
        if score_sheet_completion_form.is_valid():
            score_sheet_completion_form.save()
            return redirect('week', s.match.week.id)
    else:
        score_sheet_completion_form = ScoreSheetCompletionForm(
            instance=s,
        )

    context = {
        'score_sheet': s,
        'games_formset': score_sheet_game_formset,
        'away_player_score_sheet_summaries': s.player_summaries('away'),
        'home_player_score_sheet_summaries': s.player_summaries('home'),
        'score_sheet_completion_form': score_sheet_completion_form,
    }
    return render(request, 'stats/score_sheet_complete.html', context)


def score_sheet_edit(request, score_sheet_id):
    s = get_object_or_404(ScoreSheet, id=score_sheet_id)
    if not user_can_edit_scoresheet(request, score_sheet_id):
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
    lineup_m = getattr(s, '{}_lineup'.format(away_home))
    lineup_queryset = lineup_m.all()
    lineup_team = getattr(s.match, '{}_team'.format(away_home))
    lineup_model = AwayLineupEntry if away_home == 'away' else HomeLineupEntry

    class LineupForm(django.forms.ModelForm):
        # thanks to stack overflow for this, from here:
        # http://stackoverflow.com/questions/1982025/django-form-from-related-model
        player = django.forms.ModelChoiceField(
            queryset=lineup_team.players.all(),
            required=False,
        )

    lineup_formset_f = modelformset_factory(
        model=lineup_model,
        fields=['player'],
        form=LineupForm,
        formset=LineupFormSet,
        extra=0,
        max_num=len(PlayPosition.objects.all()),
    )

    if request.method == 'POST':
        lineup_formset = lineup_formset_f(request.POST, queryset=lineup_queryset)
        if lineup_formset.is_valid():
            lineup_formset.save()
            s.set_games()
            return redirect('score_sheet_edit', score_sheet_id=s.id)
        else:
            logging.debug("validation errors:{}".format(lineup_formset.form.non_field_errors))
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

    already_used_players = []
    # first exclude players already in the lineup
    for x in getattr(s, '{}_lineup'.format(away_home)).all():
        if x.player is not None:
            already_used_players.append(x.player.id)

    scoresheet_team = getattr(s.match, '{}_team'.format(away_home))
    substitution_players_queryset = scoresheet_team.players.all().exclude(id__in=already_used_players)
    substitution_model = AwaySubstitution if away_home == 'away' else HomeSubstitution
    substitution_queryset = getattr(s, '{}_substitutions'.format(away_home)).all()
    add_substitution_function = getattr(s, '{}_substitutions'.format(away_home))

    class SubstitutionForm(django.forms.ModelForm):
        player = django.forms.ModelChoiceField(
            queryset=substitution_players_queryset,
            required=False,
        )

    substitution_formset_f = modelformset_factory(
        model=substitution_model,
        form=SubstitutionForm,
        fields=['game_order', 'player'],
        # this may not work for leagues where the game group size is for some reason not the
        # same as the number of players in a lineup
        max_num=len(scoresheet_team.players.all()) - settings.LEAGUE['game_group_size'],
        can_delete=True,
    )

    if request.method == 'POST':
        substitution_formset = substitution_formset_f(
            request.POST, queryset=substitution_queryset
        )
        if substitution_formset.is_valid():
            logging.debug('saving {} subs for {}'.format(away_home, s.match))
            for substitution in substitution_formset.save():
                logging.debug('adding {} as {} in game {}'.format(
                    substitution.player, substitution.play_position, substitution.game_order))
                add_substitution_function.add(substitution)
            s.set_games()
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
