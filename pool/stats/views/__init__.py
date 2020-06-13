import logging

from django.shortcuts import redirect

from .season import set_season

logger = logging.getLogger(__name__)


def index(request):
    return redirect('teams')


