from django.shortcuts import redirect, render, get_object_or_404

from ..models import Tournament, Participant, Bracket, Round, TournamentMatchup

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
    check_season(request)

    a_tournament = Tournament.objects.get(id=tournament_id)
    context = {
        'tournament': a_tournament,
    }
    return render(request, 'stats/tournament.html', context)

