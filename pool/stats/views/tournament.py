import json

from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, render
from django.forms import modelform_factory, modelformset_factory
from django.db.models import Q

from ..forms import TournamentForm, TournamentParticipantForm
from ..models import Participant, Player, Season, Tournament, TournamentMatchup

from ..views import check_season


def tournaments(request, season_id=None):
    check_season(request)
    if season_id is None:
        return redirect('tournaments', season_id=request.session['season_id'])
    tournament_list = Tournament.objects.filter(season=season_id)
    context = {
        'tournaments': tournament_list,
    }
    return render(request, 'stats/tournaments.html', context)


def tournament(request, tournament_id):

    a_tournament = Tournament.objects.get(id=tournament_id)
    accept = request.META.get('HTTP_ACCEPT')
    if accept == 'application/json':

        response_dict = dict(
            id=a_tournament.id,
            name=a_tournament.name,
            type=a_tournament.type,
            elimination=a_tournament.elimination,
            season=a_tournament.season_id,
            participants=[participant.to_dict() for participant in a_tournament.participant_set.all()],
        )

        # now the matchups
        response_dict.update(brackets=[])
        for bracket in a_tournament.bracket_set.all():
            this_bracket_round_list = []
            for round in bracket.round_set.all():
                this_round = {
                    'number': round.number,
                    'matchups': []
                }
                for matchup in round.tournamentmatchup_set.all():
                    this_round['matchups'].append({
                            'number': matchup.number,
                            'id': matchup.id,
                            'participant_a': None if not matchup.participant_a else matchup.participant_a.to_dict(),
                            'participant_b': None if not matchup.participant_b else matchup.participant_b.to_dict(),
                            'winner': None if not matchup.winner else matchup.winner.to_dict(),
                    })
                this_bracket_round_list.append(this_round)
            response_dict['brackets'].append({
                'type': bracket.type, 'rounds': this_bracket_round_list
            })

        return JsonResponse(response_dict, safe=False)
    context = {
        'tournament': a_tournament,
    }
    return render(request, 'stats/tournament.html', context)


def tournament_edit(request, tournament_id=None):

    t = None
    if tournament_id is not None:
        t = Tournament.objects.get(id=tournament_id)

    if request.method == 'POST':
        tournament_form = TournamentForm(
            request.POST,
            instance=t
        )
        saved_tournament = tournament_form.save()
        # also set the season, which isn't in the form
        saved_tournament.season_id = request.session.get('season_id', Season.objects.get(is_default=True).id)
        saved_tournament.save()
        return redirect('tournament_edit', saved_tournament.id)
    else:
        tournament_form = TournamentForm(
            instance=t,
        )
    context = {
        'tournament_form': tournament_form,
    }
    return render(request, 'stats/tournament_edit.html', context)


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
            print("marking winner of matchup {} as {}".format(matchup_id, winner_id))
            matchup = TournamentMatchup.objects.get(id=matchup_id)
            winner = Participant.objects.get(id=winner_id)
            matchup.winner = winner
            matchup.save()

            update_affected_matchups(matchup)

    return HttpResponse(status=204)


def tournament_participants(request, tournament_id):

    a_tournament = Tournament.objects.get(id=tournament_id)

    participant_formset_f = modelformset_factory(
        model=Participant,
        form=TournamentParticipantForm,
        extra=2,
        can_delete=True,
    )
    participant_formset = participant_formset_f(
        queryset=Participant.objects.filter(tournament=a_tournament),
    )

    if request.method == 'POST':
        participant_formset = participant_formset_f(
            request.POST,
            queryset=Participant.objects.filter(tournament=a_tournament),
        )
        if participant_formset.is_valid():
            for pform in participant_formset:
                if pform.cleaned_data.get('DELETE', False):
                    p = Participant.objects.get(id=pform.instance.id)
                    p.delete()
                obj = pform.save(commit=False)
                obj.tournament = a_tournament
                # also set the participant type, ugly hack alert here
                obj.type = 'player'
            participant_formset.save()
        return redirect('tournament_participants', a_tournament.id)


    context = {
        'tournament': a_tournament,
        'players': Player.objects.all(),
        'participant_formset': participant_formset,
    }

    return render(request, 'stats/tournament_participants.html', context)


def tournament_brackets(request, tournament_id):

    finals_rounds = ['first', 'second']
    t = Tournament.objects.get(id=tournament_id)
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
