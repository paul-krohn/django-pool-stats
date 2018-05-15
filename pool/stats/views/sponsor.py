from django.shortcuts import get_object_or_404, render

from ..models import Sponsor


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
