from django.shortcuts import redirect, render, reverse, get_object_or_404
from django.http import JsonResponse, HttpResponse

from ..models import Game

from .score_sheet import user_can_edit_scoresheet

def update(request):

    if request.POST:

        game = get_object_or_404(Game, {
            'id': request.POST.get('game_id')
        })
        score_sheet = game.scoresheet_set.first()
        if user_can_edit_scoresheet(score_sheet):
            game.winner = request.POST.get('winner')
            game.forfeit = request.POST.get('forfeit')
            game.table_run = request.POST.get('table_run')
            game.save()
            return JsonResponse({'message': "game {} saved"})
        else:
            return HttpResponse(status=403)
