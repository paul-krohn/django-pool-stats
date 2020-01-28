import logging

import django.forms
from django.conf import settings
from django.forms import modelformset_factory
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect

from ..forms import DisabledScoreSheetGameForm, ScoreSheetGameForm, ScoreSheetCompletionForm, \
    ScoreSheetStatusForm, LineupFormSet, SubstitutionFormSet
from ..models import ScoreSheet, Game, Match, AwayLineupEntry, HomeLineupEntry, PlayPosition, AwaySubstitution, \
    HomeSubstitution
from ..utils import session_uid, is_stats_master


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
        'auto_save': request.session.get('auto_save', False),
        'score_sheet': s,
        'game_group_size': settings.LEAGUE['game_group_size'],
        'edit_link': user_can_edit_scoresheet(request, score_sheet_id),
        'games_formset': score_sheet_game_formset,
        'away_player_score_sheet_summaries': s.player_summaries('away'),
        'home_player_score_sheet_summaries': s.player_summaries('home')
    }
    return render(request, 'stats/score_sheet.html', context)


def score_sheet_games(score_sheet_id):
    game_list = []

    s = ScoreSheet.objects.get(id=score_sheet_id)
    for game in s.games.all():
        game_list.append(game.as_dict())
    return game_list

def score_sheet_summary(request, score_sheet_id):
    s = get_object_or_404(ScoreSheet, id=score_sheet_id)
    summary = s.summary()
    game_list = []
    for game in s.games.all():
        game_list.append(game.as_dict())

    summary.update({'games': game_list})
    summary.update({'editable': user_can_edit_scoresheet(request, score_sheet_id)})
    return JsonResponse(summary)

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
        'auto_save': request.session.get('auto_save', False),
        'game_group_size': settings.LEAGUE['game_group_size'],
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


def score_sheet_copy(request):

    if request.method == 'POST' and 'scoresheet_id' in request.POST:
        s = ScoreSheet.objects.get(id=request.POST['scoresheet_id'])
        # don't copy 'official' score sheets, that would be bad!
        if s.official == 1:
            return redirect('score_sheet', request.POST['scoresheet_id'])
        new_scoresheet_id = s.copy(session_id=session_uid(request))
        return redirect('score_sheet_edit', new_scoresheet_id)
    else:
        return HttpResponseBadRequest


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


def user_can_edit_scoresheet(request, score_sheet_id):

    s = ScoreSheet.objects.get(id=score_sheet_id)
    # you can edit a score sheet if it is not official and either you created it,
    # or you are an admin
    return s.official != 1 and ((session_uid(request) == s.creator_session) or
                                request.user.is_superuser or is_stats_master(request.user))
