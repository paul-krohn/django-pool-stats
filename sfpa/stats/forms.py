import django.forms
from .models import Player, Team, Season


class PlayerForm(django.forms.ModelForm):
    class Meta:
        model = Player
        exclude = []
    # field1 = forms.ModelChoiceField(queryset=..., empty_label="(Nothing)")
    team = django.forms.ModelChoiceField(queryset=Team.objects.filter(season__exact=1))
