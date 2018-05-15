import time
import datetime

from django.shortcuts import render, redirect, get_object_or_404
from ..models import Division, AwayLineupEntry, Game, HomeLineupEntry, Match, Player, \
    ScoreSheet, Season, Sponsor, Team, Week
from ..models import PlayPosition
from ..models import PlayerSeasonSummary
from ..models import AwaySubstitution, HomeSubstitution
from ..forms import PlayerForm, ScoreSheetGameForm, DisabledScoreSheetGameForm, ScoreSheetCompletionForm
from ..forms import ScoreSheetStatusForm
from ..forms import LineupFormSet, SubstitutionFormSet
from django.forms import modelformset_factory

import django.forms
import django.db.models
from django.conf import settings

from django.core.cache import cache
from django.views.decorators.cache import never_cache
from django.utils.cache import get_cache_key
from django.urls import reverse
from django.http import HttpResponseBadRequest


import logging
logger = logging.getLogger(__name__)


def session_uid(request):
    if 'uid' not in request.session.keys():
        request.session['uid'] = str(hash(time.time()))[0:15]
    return request.session['uid']


def expire_page(request, path=None, query_string=None, method='GET'):
    """
    :param request: "real" request, or at least one providing the same scheme, host, and port as what you want to expire
    :param path: The path you want to expire, if not the path on the request
    :param query_string: The query string you want to expire, as opposed to the path on the request
    :param method: the HTTP method for the page, if not GET
    :return: None
    """
    if query_string is not None:
        request.META['QUERY_STRING'] = query_string
    if path is not None:
        request.path = path
    request.method = method

    # get_raw_uri and method show, as of this writing, everything used in the cache key
    # print('req uri: {} method: {}'.format(request.get_raw_uri(), request.method))
    key = get_cache_key(request)
    if key in cache:
        cache.delete(key)


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


def is_stats_master(user):
    return user.groups.filter(name='statsmaster').exists()


def user_can_edit_scoresheet(request, score_sheet_id):

    s = ScoreSheet.objects.get(id=score_sheet_id)
    # you can edit a score sheet if it is not official and either you created it,
    # or you are an admin
    if (not s.official) and ((session_uid(request) == s.creator_session) or
                             request.user.is_superuser or is_stats_master(request.user)):
        return True
    else:
        return False


def check_season(request):
    if 'season_id' in request.session:
        return
    else:
        set_season(request)


def index(request):
    check_season(request)
    return redirect('teams', season_id=request.session['season_id'])


@never_cache
def get_current_week(request, today_date=''):

    check_season(request)
    # now get the time range that is Sun-Sat this week; start with the DOW now
    today = datetime.date.today()
    if today_date != '':  # this param is really just here for tests.
        # print('we got the arg: {}'.format(today_date))
        (year, month, day) = today_date.split('-')
        today = datetime.date(year=int(year), month=int(month), day=int(day))

    # in datetime, Monday -> 0 :/
    prev_sunday = today - datetime.timedelta(days=(today.weekday()+1))
    next_saturday = prev_sunday + datetime.timedelta(days=6)

    _weeks = Week.objects.filter(
        date__lt=next_saturday,
        date__gt=prev_sunday,
        season_id=request.session['season_id'],
    ).order_by('date')

    if len(_weeks) == 1:
        # print('redirecting to {}/{}'.format(_weeks[0], _weeks[0].date))
        return redirect('week', week_id=_weeks[0].id)
    elif len(_weeks) == 2:
        closest_week = _weeks[0]
        closest_week_gap = abs(today - _weeks[0].date)
        for _week in _weeks:
            if abs(today - _week.date) < closest_week_gap:
                closest_week_gap = abs(_week.date - today)
                closest_week = _week
        # print('redirecting to {}/{}'.format(closest_week, closest_week.date))
        return redirect('week', week_id=closest_week.id)
    else:
        return redirect('weeks')


def teams(request, season_id=None):
    check_season(request)
    if season_id is None:
        return redirect('teams', season_id=request.session['season_id'])
    team_list = Team.objects.filter(season=season_id).order_by('-win_percentage')
    season = Season.objects.get(id=request.session['season_id'])
    context = {
        'teams': team_list,
        'season': season,
    }
    return render(request, 'stats/teams.html', context)


def player(request, player_id):
    check_season(request)
    _player = get_object_or_404(Player, id=player_id)
    summaries = PlayerSeasonSummary.objects.filter(player__exact=_player).order_by('-season')
    _score_sheets_with_dupes = ScoreSheet.objects.filter(official=True).filter(
        django.db.models.Q(away_lineup__player=_player) |
        django.db.models.Q(home_lineup__player=_player) |
        django.db.models.Q(away_substitutions__player=_player) |
        django.db.models.Q(home_substitutions__player=_player)
    ).order_by('match__week__date').filter(match__week__season=request.session['season_id'])
    # there are dupes in _score_sheets at this point, so we have to remove them; method is cribbed from:
    # http://stackoverflow.com/questions/480214/how-do-you-remove-duplicates-from-a-list-in-python-whilst-preserving-order
    seen = set()
    seen_add = seen.add
    _score_sheets = [x for x in _score_sheets_with_dupes if not (x in seen or seen_add(x))]
    score_sheet_summaries = []
    # now scrape through the score sheets; collect games from each scoresheet, with win true/falsed and TRs marked
    for _score_sheet in _score_sheets:
        this_score_sheet = {
            'id': _score_sheet.id,
            'match': _score_sheet.match,
            'games': []
        }
        for game in _score_sheet.games.all():
            if not game.winner or game.forfeit or game.away_player is None or game.home_player is None:
                continue  # skip not-won games, ie forfeits and unplayed playoff games
            # if _player.id not in [game.away_player.id, game.home_player.id]:
            if _player not in [game.away_player, game.home_player]:
                continue  # skip games not involving this player
            this_game = {
                'table_run': game.table_run,
                'opponent': game.home_player,
                'win': game.winner == 'away',
            }
            if _player == game.home_player:
                this_game['opponent'] = game.away_player
                this_game['win'] = game.winner == 'home'
            this_score_sheet['games'].append(this_game)
        score_sheet_summaries.append(this_score_sheet)
    context = {
        'score_sheet_summaries': score_sheet_summaries,
        'summaries': summaries,
        'player': _player,
    }
    rendered_page = render(request, 'stats/player.html', context)
    return rendered_page


def players(request, season_id=None):
    check_season(request)

    if season_id is None:
        return redirect('players', season_id=request.session['season_id'])

    _players = PlayerSeasonSummary.objects.filter(
        season=season_id,
        ranking__gt=0
    ).order_by('-win_percentage', '-wins')
    show_teams = True

    context = {
        'players': _players,
        'show_teams': show_teams,  # referenced in the player_table.html template
        'season_id': request.session['season_id'],
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


def team(request, team_id, after=None):

    check_season(request)

    _team = get_object_or_404(Team, id=team_id)
    _players = PlayerSeasonSummary.objects.filter(
        player_id__in=list([x.id for x in _team.players.all()]),
        season_id=_team.season.id,
    ).order_by('player__last_name')
    official_score_sheets = ScoreSheet.objects.filter(official=True).filter(
        django.db.models.Q(match__away_team=_team) | django.db.models.Q(match__home_team=_team)
    ).order_by('match__week__date')
    unofficial_score_sheets = ScoreSheet.objects.filter(official=False).filter(
        django.db.models.Q(match__away_team=_team) | django.db.models.Q(match__home_team=_team)
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
        django.db.models.Q(away_team=_team) | django.db.models.Q(home_team=_team)
    ).order_by('week__date')

    context = {
        'team': _team,
        'players': _players,
        'show_players': False,
        'official_score_sheets': official_score_sheets,
        'unofficial_score_sheets': unofficial_score_sheets,
        'matches': _matches,
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


def divisions(request, season_id=None):
    check_season(request)
    if season_id is None:
        return redirect('divisions', season_id=request.session['season_id'])
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
    return render(request, 'stats/divisions.html', context)


class ScoreSheetCreationForm(django.forms.ModelForm):

    class Meta:
        model = Match
        # fields = ['id']
        exclude = []


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


def score_sheet_edit(request, score_sheet_id):
    s = get_object_or_404(ScoreSheet, id=score_sheet_id)
    if not user_can_edit_scoresheet(request, score_sheet_id):
        return redirect('score_sheet', s.id)
    score_sheet_game_formset_f = modelformset_factory(
        Game,
        form=ScoreSheetGameForm,
        max_num=len(s.games.all())
    )

    # normally, you would populate a formset conditionally on whether the request is a POST or not;
    # in this case, the lineups and substitutions are posted to a different view, so that is not necessary.
    away_lineup_formset = score_sheet_lineup_formset(
        score_sheet_id=score_sheet_id, away_home='away')(queryset=s.away_lineup.all())
    home_lineup_formset = score_sheet_lineup_formset(
        score_sheet_id=score_sheet_id, away_home='home')(queryset=s.home_lineup.all())
    away_substitutions_formset = substitutions_formset_factory_builder(
        score_sheet_id=score_sheet_id, away_home='away')(queryset=s.away_substitutions.all())
    home_substitutions_formset = substitutions_formset_factory_builder(
        score_sheet_id=score_sheet_id, away_home='home')(queryset=s.home_substitutions.all())

    if request.method == 'POST':
        score_sheet_completion_form = ScoreSheetCompletionForm(request.POST, instance=s)
        if is_stats_master(request.user):
            score_sheet_completion_form = ScoreSheetStatusForm(request.POST, instance=s)
        score_sheet_game_formset = score_sheet_game_formset_f(
            request.POST, queryset=s.games.all()
        )
        # save either the completion form, or the games. It would be preferable to save both, but one
        # runs in to management form complications.
        if 'games' in request.POST:
            if score_sheet_game_formset.is_valid():
                score_sheet_game_formset.save()
        else:
            if score_sheet_completion_form.is_valid():
                score_sheet_completion_form.save()
                if score_sheet_completion_form.instance.complete:
                    return redirect('week', s.match.week.id)
    else:
        score_sheet_completion_form = ScoreSheetCompletionForm(
            instance=s,
        )
        if is_stats_master(request.user):
            score_sheet_completion_form = ScoreSheetStatusForm(instance=s)

        score_sheet_game_formset = score_sheet_game_formset_f(
            queryset=s.games.all(),
        )

    context = {
        'score_sheet': s,
        'games_formset': score_sheet_game_formset,
        'away_lineup_formset': away_lineup_formset,
        'home_lineup_formset': home_lineup_formset,
        'away_substitutions_formset': away_substitutions_formset,
        'home_substitutions_formset': home_substitutions_formset,
        'away_player_score_sheet_summaries': s.player_summaries('away'),
        'home_player_score_sheet_summaries': s.player_summaries('home'),
        'score_sheet_completion_form': score_sheet_completion_form,
    }
    return render(request, 'stats/score_sheet_edit.html', context)


def score_sheet_create(request):

    if request.method == 'POST' and 'match_id' in request.POST:
        s = ScoreSheet(match=Match.objects.get(id=request.POST['match_id']))
        s.creator_session = session_uid(request)
        s.save()
        s.initialize_lineup()
        s.initialize_games()

        return redirect('score_sheet_edit', score_sheet_id=s.id)
    else:
        return HttpResponseBadRequest()


def score_sheet_lineup_formset(score_sheet_id, away_home):
    s = ScoreSheet.objects.get(id=score_sheet_id)

    # it would be prettier to do this by passing kwargs but,
    # it seems you can't do that with a ModelForm so, the ugly is here.
    lineup_team = getattr(s.match, '{}_team'.format(away_home))
    lineup_model = AwayLineupEntry if away_home == 'away' else HomeLineupEntry

    class LineupForm(django.forms.ModelForm):
        # thanks to stack overflow for this, from here:
        # http://stackoverflow.com/questions/1982025/django-form-from-related-model
        player = django.forms.ModelChoiceField(
            queryset=lineup_team.players.all(),
            required=False,
        )

    return modelformset_factory(
        model=lineup_model,
        fields=['player'],
        form=LineupForm,
        formset=LineupFormSet,
        extra=0,
        max_num=len(PlayPosition.objects.all()),
    )


def score_sheet_lineup(request, score_sheet_id, away_home):
    s = ScoreSheet.objects.get(id=score_sheet_id)

    lineup_m = getattr(s, '{}_lineup'.format(away_home))
    lineup_queryset = lineup_m.all()

    lineup_formset_f = score_sheet_lineup_formset(score_sheet_id, away_home)

    if request.method == 'POST':
        lineup_formset = lineup_formset_f(request.POST, queryset=lineup_queryset)
        if lineup_formset.is_valid():
            lineup_formset.save()
            s.set_games()
            return redirect('score_sheet_edit', score_sheet_id=s.id)
        else:
            logging.debug("validation errors:{}".format(lineup_formset.form.non_field_errors))
    else:
        return redirect('score_sheet_edit', score_sheet_id=s.id)

    context = {
        'score_sheet': s,
        'lineup_formset': lineup_formset,
        'away_home': away_home
    }
    return render(request, 'stats/score_sheet_lineup_edit_standalone.html', context)


def substitutions_formset_factory_builder(score_sheet_id, away_home):
    s = ScoreSheet.objects.get(id=score_sheet_id)
    already_used_players = []
    # first exclude players already in the lineup, but not the player in tiebreaker position
    for x in getattr(s, '{}_lineup'.format(away_home)).filter(position__tiebreaker=False):
        if x.player is not None:
            already_used_players.append(x.player.id)

    score_sheet_team = getattr(s.match, '{}_team'.format(away_home))
    substitution_players_queryset = score_sheet_team.players.all().exclude(id__in=already_used_players)
    substitution_model = AwaySubstitution if away_home == 'away' else HomeSubstitution

    class SubstitutionForm(django.forms.ModelForm):
        player = django.forms.ModelChoiceField(
            queryset=substitution_players_queryset,
            required=False,
        )

    return modelformset_factory(
        model=substitution_model,
        form=SubstitutionForm,
        formset=SubstitutionFormSet,
        fields=['game_order', 'player'],
        # this may not work for leagues where the game group size is for some reason not the
        # same as the number of players in a lineup
        max_num=len(score_sheet_team.players.all()) - settings.LEAGUE['game_group_size'],
        can_delete=True,
    )


def score_sheet_substitutions(request, score_sheet_id, away_home):
    s = ScoreSheet.objects.get(id=score_sheet_id)

    substitution_queryset = getattr(s, '{}_substitutions'.format(away_home)).all()
    add_substitution_function = getattr(s, '{}_substitutions'.format(away_home))

    substitution_formset_f = substitutions_formset_factory_builder(s.id, away_home)

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
            logging.debug("validation errors:{}".format(substitution_formset.form.non_field_errors))
            context = {
                'score_sheet': s,
                'substitutions_formset': substitution_formset,
                'away_home': away_home
            }
            return render(request, 'stats/score_sheet_substitutions_standalone.html', context)

    else:
        return redirect('score_sheet_edit', score_sheet_id=s.id)


def update_stats(request):
    # be sure about what season we are working on
    check_season(request)
    season_id = request.session['season_id']

    Team.update_teams_stats(season_id=season_id)
    # cache invalidation has to be called from a view, because we need access to a
    # request object to find the cache key.
    expire_args = {'season_id': season_id}
    expire_page(request, reverse('divisions', kwargs=expire_args))
    expire_page(request, reverse('teams', kwargs=expire_args))
    for a_team in Team.objects.filter(season_id=request.session['season_id']):
        expire_page(request, reverse('team', kwargs={'team_id': a_team.id}))

    PlayerSeasonSummary.update_all(season_id=season_id)
    for pss in PlayerSeasonSummary.objects.filter(season_id=season_id):
        expire_page(request, reverse('player', kwargs={'player_id': pss.player.id}))

    expire_page(request, reverse('players', kwargs={'season_id': season_id}))

    return redirect('teams')
