import django.forms
from .models import Player, Team, Game, ScoreSheet, Week
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


class SubstitutionFormSet(django.forms.BaseModelFormSet):
    def clean(self):
        super(SubstitutionFormSet, self).clean()

        player_values = []
        for form in self.forms:
            # if form.cleaned_data['id'].position.tiebreaker:
            #     continue
            if 'player' in form.cleaned_data.keys() and form.cleaned_data['player'] is not None:
                player_values.append(form.cleaned_data['player'])
        if len(player_values) > len(set(player_values)):
            raise ValidationError('You may not substitute in the same player twice',
                                  code='lineup_duplicate_player')


class MatchForm(django.forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(MatchForm, self).__init__(*args, **kwargs)

        # we need the list of teams in this match, to pass them to Week.used_teams, so
        # it can return them in the list of teams to choose from displayed in the match admin form.
        this_match_teams = []
        if hasattr(self.instance, 'away_team') and hasattr(self.instance.away_team, 'id'):
            this_match_teams.append(self.instance.away_team.id)
        if hasattr(self.instance, 'home_team') and hasattr(self.instance.home_team, 'id'):
            this_match_teams.append(self.instance.home_team.id)

        if hasattr(self.instance, 'week'):
            for loc in ['away', 'home']:
                self.fields['{}_team'.format(loc)].queryset = Team.objects.filter(
                    season__is_default=True).exclude(
                    id__in=self.instance.week.used_teams(teams=this_match_teams)
                )
        else:
            self.fields['away_team'].queryset = Team.objects.filter(season__is_default=True)
            self.fields['home_team'].queryset = Team.objects.filter(season__is_default=True)
