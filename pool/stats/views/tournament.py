from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, render
from django.forms import modelformset_factory
from django.db.models import Q

from ..forms import TournamentForm, TournamentParticipantFormSet, create_tournament_participant_form
from ..models import Participant, Player, Season, Tournament, TournamentMatchup
from ..utils import session_uid
from ..views import check_season


def tournaments(request, season_id=None):
    check_season(request)
    if season_id is None:
        return redirect('tournaments', season_id=request.session['season_id'])
    tournament_list = Tournament.objects.filter(season=season_id)
    context = {
        'tournaments': tournament_list,
    }
    return render(request, 'stats/tournament/list.html', context)


def tournament(request, tournament_id):

    a_tournament = Tournament.objects.get(id=tournament_id)
    accept = request.META.get('HTTP_ACCEPT')
    if accept == 'application/json':
        return JsonResponse(a_tournament.as_dict(request), safe=False)
    context = {
        'tournament': a_tournament,
    }
    return render(request, 'stats/tournament/view.html', context)


def tournament_edit(request, tournament_id=None):

    t = None
    if tournament_id is not None:
        t = Tournament.objects.get(id=tournament_id)
        if not t.editable(request):
            return redirect('tournament', t.id)

    if request.method == 'POST':

        tournament_form = TournamentForm(
            request.POST,
            instance=t
        )
        saved_tournament = tournament_form.save()
        # also set the season, which isn't in the form
        saved_tournament.season_id = request.session.get('season_id', Season.objects.get(is_default=True).id)
        # also set the creator session
        saved_tournament.creator_session = session_uid(request)
        saved_tournament.save()
        return redirect('tournament_edit', saved_tournament.id)
    else:
        tournament_form = TournamentForm(
            instance=t,
        )
    context = {
        'tournament_form': tournament_form,
        'setup_disabled': 'disabled',
        'brackets_disabled': 'disabled',
        'participants_disabled': '' if tournament_id else 'disabled',
    }
    return render(request, 'stats/tournament/edit.html', context)


def update_affected_matchups(a_matchup):
    affected_matchups = TournamentMatchup.objects.filter(
        Q(source_match_a=a_matchup) | Q(source_match_b=a_matchup)
    )
    for m in affected_matchups:
        m.update()


def tournament_mark_winner(request):

    if request.method == 'POST':
        matchup_id = request.POST.get('matchup')
        winner_id = request.POST.get('winner')
        if matchup_id and winner_id:
            matchup = TournamentMatchup.objects.get(id=matchup_id)
            if not matchup.round.bracket.tournament.editable(request):
                return HttpResponse(status=403)
            print("marking winner of matchup {} as {}".format(matchup_id, winner_id))
            winner = Participant.objects.get(id=winner_id)
            matchup.winner = winner
            matchup.save()

            update_affected_matchups(matchup)

    return HttpResponse(status=204)


def tournament_participants(request, tournament_id):

    a_tournament = Tournament.objects.get(id=tournament_id)
    if not a_tournament.editable(request):
        return redirect('tournament', a_tournament.id)

    participant_form = create_tournament_participant_form(a_tournament)

    participant_formset_f = modelformset_factory(
        formset=TournamentParticipantFormSet,
        model=Participant,
        form=participant_form,
        extra=2,
        can_delete=True,
    )
    participant_queryset = Participant.objects.filter(tournament=a_tournament)
    participant_formset = participant_formset_f(
        queryset=participant_queryset,
    )

    if request.method == 'POST':
        participant_formset = participant_formset_f(
            request.POST,
            queryset=participant_queryset,
        )

        if participant_formset.is_valid():
            for pform in participant_formset:
                if pform.cleaned_data.get('DELETE', False) and pform.cleaned_data.get('pk', False):
                    p = Participant.objects.get(id=pform.instance.id)
                    p.delete()
                obj = pform.save(commit=False)
                obj.tournament = a_tournament
                # also set the participant type, ugly hack alert here
                obj.type = 'player'
                if a_tournament.type == 'teams':
                    obj.type = 'team'
            participant_formset.save()
            if a_tournament.seeded:
                a_tournament.update_seeds()
            else:
                a_tournament.randomize_seeds()
            return redirect('tournament_participants', a_tournament.id)
    # TODO: make double-elimination, 2-participant tournaments work
    min_size = 2
    if a_tournament.elimination == 'double':
        min_size = 4
    brackets_disabled = ''
    if a_tournament.bracket_size() < min_size:
        brackets_disabled = 'disabled'

    context = {
        'tournament': a_tournament,
        'players': Player.objects.all(),
        'participant_formset': participant_formset,
        'setup_disabled': 'disabled' if len(a_tournament.bracket_set.all()) else '',
        'brackets_disabled': brackets_disabled,
        'participants_disabled': 'disabled',
    }

    return render(request, 'stats/tournament/participants.html', context)


def tournament_brackets(request, tournament_id):

    finals_rounds = ['first', 'second']
    t = Tournament.objects.get(id=tournament_id)
    if not t.editable(request):
        return redirect('tournament', t.id)
    t.create_brackets()
    t.create_rounds()

    for b in t.bracket_set.all():
        for r in b.round_set.all():
            r.create_matchups()
    if t.elimination == 'double':
        winners_bracket = t.bracket_set.get(type='w')
        i = 0
        for _round in winners_bracket.round_set.filter(number__gt=t.round_count()).order_by('number'):
            _round.create_finals_matchup(finals_rounds[i])
            i += 1
            pass
    return redirect('tournament', tournament_id)
