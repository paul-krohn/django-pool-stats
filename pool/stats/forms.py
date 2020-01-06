import django.forms
from django.core.exceptions import ValidationError

from .models import Game, Match, Player, ScoreSheet, Table, Team
from .utils import get_dupes_from_dict
from .models import Participant, Player, PlayerSeasonSummary, Team, Game, ScoreSheet, Tournament, Match
from .views.season import get_default_season

WINNER_CHOICES = (
    ('home', 'Home'),
    ('away', 'Away'),
    ('', None)
)


class TeamForm(django.forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(TeamForm, self).__init__(*args, **kwargs)

        default_season = get_default_season()

        if getattr(self.instance, 'id') is None:
            self.fields['captain'].queryset = Player.objects.none()
        else:
            self.fields['captain'].queryset = self.instance.players.all()
        self.fields['season'].initial = default_season


class PlayerForm(django.forms.ModelForm):
    class Meta:
        model = Player
        exclude = []
    team = django.forms.ModelChoiceField(queryset=Team.objects.filter(season__is_default__exact=True))


class ScoreSheetGameForm(django.forms.ModelForm):

    class Meta:
        model = Game
        fields = ['winner', 'table_run', 'forfeit', 'timestamp']
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


class ScoreSheetStatusForm(django.forms.ModelForm):

    class Meta:
        model = ScoreSheet
        fields = ['comment', 'complete', 'official']


class TournamentForm(django.forms.ModelForm):
    class Meta:
        model = Tournament
        exclude = ['season']
        widgets = {
            'name': django.forms.TextInput(),
        }


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


class ScoreSheetCreationForm(django.forms.ModelForm):

    class Meta:
        model = Match
        exclude = []


class TeamRegistrationForm(django.forms.ModelForm):

    table = django.forms.ModelChoiceField(queryset=Table.objects.filter(active=True))

    def __init__(self, *args, **kwargs):
        super(TeamRegistrationForm, self).__init__(*args, **kwargs)
        self.fields['table'].required = False

    class Meta:
        model = Team
        fields = ['name', 'captain', 'players', 'table']
        widgets = {
            'name': django.forms.TextInput(),
        }


class TeamPlayerFormSet(django.forms.BaseModelFormSet):

    class Meta:
        model = Player
        exclude = []  # TODO fix

    def clean(self):
        super().clean()

        players = {}
        player_count = 0
        for form in self.forms:
            if form.cleaned_data == {}:
                pass  # there is an empty form in every formset; assume that is valid
            elif 'DELETE' in form.cleaned_data and form.cleaned_data['DELETE'] is True:
                pass  # assume deletions are valid
            form_player = form.cleaned_data.get('player')
            if form_player:
                player_count += 1
                if form_player in players:
                    players[form_player] += 1
                else:
                    players[form_player] = 1
        if len(players) < player_count:
            raise ValidationError('there are duplicate players: {}'.format(', '.join(
                get_dupes_from_dict(players)
            )))



class SubstitutionFormSet(django.forms.BaseModelFormSet):
    def clean(self):
        super(SubstitutionFormSet, self).clean()

        player_values = []
        for form in self.forms:
            if form.cleaned_data == {}:
                pass  # there is an empty form in every formset; assume that is valid
            elif 'DELETE' in form.cleaned_data and form.cleaned_data['DELETE'] is True:
                pass  # assume deletions are valid
            elif 'player' in form.cleaned_data and form.cleaned_data['player'] is not None and \
                    'game_order' in form.cleaned_data and form.cleaned_data['game_order'] is not None:
                player_values.append(form.cleaned_data['player'])
            else:
                raise ValidationError("You must set the player and the game order of each substitution")
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
                    id__in=self.instance.week.used_teams(team_ids=this_match_teams)
                )
        else:
            self.fields['away_team'].queryset = Team.objects.filter(season__is_default=True)
            self.fields['home_team'].queryset = Team.objects.filter(season__is_default=True)
        self.fields['season'].initial = get_default_season()


class MatchupForm(django.forms.Form):

    kind = django.forms.ChoiceField(
        widget=django.forms.RadioSelect(attrs={"onChange": "$('#id_thing').val('');$('#the_form').submit()"}),
        choices=[('match', 'match'), ('scoresheet', 'scoresheet')],
        required=False,
        label='',
    )
    week = django.forms.CharField(required=False, widget=django.forms.HiddenInput)
    thing = django.forms.CharField(required=False, widget=django.forms.HiddenInput)


def create_tournament_participant_form(a_tournament):

    participant_field = 'player'
    participant_form_fields = ['player', 'tournament']
    participant_queryset = Player.objects.filter(
        id__in=[pss.player.id for pss in PlayerSeasonSummary.objects.filter(season_id=a_tournament.season_id)]
    )
    if a_tournament.type == 'teams':
        participant_queryset = Team.objects.filter(season_id=a_tournament.season_id)
        participant_field = 'team'
        participant_form_fields = ['team', 'tournament']

    class ParticipantForm(django.forms.ModelForm):

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fields['tournament'].widget = django.forms.HiddenInput()
            self.fields['tournament'].initial = a_tournament
            self.fields[participant_field].queryset = participant_queryset

        class Meta:
            model = Participant
            fields = participant_form_fields

    return ParticipantForm

