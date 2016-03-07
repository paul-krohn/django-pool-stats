import django.forms
from .models import Player


class PlayerForm(django.forms.ModelForm):
    class Meta:
        model = Player
        exclude = []
