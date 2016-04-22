import django.forms
from .models import Player, Team, Game, ScoreSheet

WINNER_CHOICES = (
    ('home', 'Home'),
    ('away', 'Away'),
)


class PlayerForm(django.forms.ModelForm):
    class Meta:
        model = Player
        exclude = []
    team = django.forms.ModelChoiceField(queryset=Team.objects.filter(season__is_default__exact=True))


class ScoreSheetGameForm(django.forms.ModelForm):

    class Meta:
        model = Game
        fields = ['winner', 'table_run', 'forfeit']
        extra = 0
        widgets = {
            'winner': django.forms.RadioSelect(
                choices=WINNER_CHOICES
            )
        }
        labels = {
            'winner': '',
            'table_run': '',
            'forfeit': '',
        }


class DisabledScoreSheetGameForm(ScoreSheetGameForm):

    def __init__(self, *args, **kwargs):
        super(DisabledScoreSheetGameForm, self).__init__(*args, **kwargs)
        self.fields['winner'].widget.attrs['disabled'] = 'disabled'
        self.fields['table_run'].widget.attrs['disabled'] = 'disabled'
        self.fields['forfeit'].widget.attrs['disabled'] = 'disabled'


class ScoreSheetCompletionForm(django.forms.ModelForm):

    class Meta:
        model = ScoreSheet
        fields = ['complete', 'comment']
