from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.forms import modelformset_factory

from ..forms import TournamentParticipantForm
from ..models import Tournament, Participant, Player

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
        response_dict.update(matchups=[])
        response_dict.update(brackets=[])
        for bracket in a_tournament.bracket_set.all():
            this_bracket_round_list = []
            for round in bracket.round_set.all():
                this_bracket_round_list.append({'id': round.id})
                for matchup in round.tournamentmatchup_set.all():
                    response_dict['matchups'].append({
                        'bracket': bracket.type,
                        'round': round.number,
                        'match': {
                            'number': matchup.number,
                            'participant_a': matchup.participant_a.to_dict() if matchup.participant_a else None,
                            'participant_b': matchup.participant_b.to_dict() if matchup.participant_b else None,
                            'winner': matchup.winner.id if matchup.winner else None,
                        }
                    })
            response_dict['brackets'].append({
                'type': bracket.type, 'rounds': this_bracket_round_list
            })

        return JsonResponse(response_dict, safe=False)
    context = {
        'tournament': a_tournament,
    }
    return render(request, 'stats/tournament.html', context)


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
            participant_formset.save()
        return redirect('tournament_participants', a_tournament.id)


    context = {
        'tournament': a_tournament,
        'players': Player.objects.all(),
        'particpant_formset': participant_formset,
    }

    return render(request, 'stats/tournament_participants.html', context)
