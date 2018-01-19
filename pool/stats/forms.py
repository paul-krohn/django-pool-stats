import django.forms
from .models import Player, Team, Game, ScoreSheet
from django.core.exceptions import ValidationError

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

    def clean(self):
        cleaned_data = super(ScoreSheetGameForm, self).clean()

        tr = cleaned_data.get('table_run')
        ff = cleaned_data.get('forfeit')

        if tr and ff:
            raise ValidationError(
                "A game can't be both a forfeit and a table run."
            )


class DisabledScoreSheetGameForm(ScoreSheetGameForm):

    def __init__(self, *args, **kwargs):
        super(DisabledScoreSheetGameForm, self).__init__(*args, **kwargs)
        self.fields['winner'].widget.attrs['disabled'] = 'disabled'
        self.fields['table_run'].widget.attrs['disabled'] = 'disabled'
        self.fields['forfeit'].widget.attrs['disabled'] = 'disabled'


class ScoreSheetCompletionForm(django.forms.ModelForm):

    class Meta:
        model = ScoreSheet
        fields = ['comment', 'complete']


class LineupFormSet(django.forms.BaseModelFormSet):
    def clean(self):
        super(LineupFormSet, self).clean()

        player_values = []
        for form in self.forms:
            if form.cleaned_data['id'].position.tiebreaker:
                continue
            if 'player' in form.cleaned_data.keys() and form.cleaned_data['player'] is not None:
                player_values.append(form.cleaned_data['player'])
        if len(player_values) > len(set(player_values)):
            raise ValidationError('All players must be unique, there is at least one player in 2 positions.',
                                  code='lineup_duplicate_player')
