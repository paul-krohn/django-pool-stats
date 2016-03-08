import django.forms
from .models import Player, Team


class PlayerForm(django.forms.ModelForm):
    class Meta:
        model = Player
        exclude = []
    team = django.forms.ModelChoiceField(queryset=Team.objects.filter(season__is_default__exact=True))
