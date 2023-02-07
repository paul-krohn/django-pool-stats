from django.contrib import admin
from django.urls import reverse
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.contrib.admin import SimpleListFilter
from django.shortcuts import redirect

from .utils import update_season_stats, expire_caches
from .models import Division, GameOrder, Match, Player, PlayPosition, WeekDivisionMatchup
from .models import ScoreAdjustment, ScoreSheet, Season, Sponsor, Table, Team, Week
from .forms import MatchForm, TeamForm, ScoreAdjustmentAdminForm
from .views.season import get_default_season

admin.AdminSite.site_header = "{} stats admin".format(settings.LEAGUE['name'])
admin.site.site_url = '/stats'


def find_duplicate_table_assignments(obj, request, week):

    used_tables = []
    double_booked_tables = []
    week_matches = Match.objects.filter(week=week)
    inc = 0
    while inc < len(week_matches):
        if week_matches[inc].table() in used_tables:
            double_booked_tables.append(week_matches[inc].table())
        used_tables.append(week_matches[inc].table())
        inc += 1
    if len(double_booked_tables):
        teams = Team.objects.filter(season_id=week.season.id)
        # used_tables = list(set([m.table() for m in ms]))
        available_tables = list(set([t.table for t in teams]))
        for used_table in used_tables:
            if used_table in available_tables:
                available_tables.remove(used_table)
        obj.message_user(
            request,
            level='ERROR',
            message='Double-booked tables: {}'.format('; '.join([d.__str__() for d in double_booked_tables])),
        )
        obj.message_user(
            request,
            level='INFO',
            message='Available tables: {}'.format('; '. join([a.__str__() for a in available_tables]))
        )
    else:
        obj.message_user(
            request,
            level='INFO',
            message='No double-booked tables.',
        )


class SeasonFilter(SimpleListFilter):
    # a custom filter that defaults to the 'default' season, instead of a 'All'
    # cribbed/modified from https://stackoverflow.com/questions/851636/default-filter-in-django-admin
    title = _('Season')

    parameter_name = 'season'

    def lookups(self, request, model_admin):
        # we want to return a list of tuples of the query value and display value;
        # in this case, all the seasons, plus 'all'
        choices = [(season.id, season) for season in Season.objects.all().order_by('-pub_date')]
        choices.append(('all', _('All')))
        return choices

    def choices(self, cl):
        for lookup, title in self.lookup_choices:
            yield {
                'selected': self.value() == lookup,
                'query_string': cl.get_query_string({
                    self.parameter_name: lookup,
                }, []),
                'display': title,
            }

    def queryset(self, request, queryset):
        if self.value() == 'all':
            return queryset
        elif self.value() is None:
            return queryset.filter(season__is_default=True)
        else:
            return queryset.filter(season=self.value())


class MatchSeasonFilter(SeasonFilter):
    # for admin views where the object's match is via the season
    parameter_name = 'match__season'

    def queryset(self, request, queryset):
        if self.value() == 'all':
            return queryset
        elif self.value() is None:
            return queryset.filter(match__season__is_default=True)
        else:
            return queryset.filter(match__season=self.value())


class DivisionAdmin(admin.ModelAdmin):
    list_filter = ['season']
    list_display = ['__str__', 'season']

    def get_form(self, request, obj=None, **kwargs):
        form = super(DivisionAdmin, self).get_form(request, obj, **kwargs)
        form.base_fields['season'].initial = get_default_season()
        return form


admin.site.register(Division, DivisionAdmin)


class PlayerAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'last_name', 'first_name', 'email']
    search_fields = ['last_name', 'first_name', 'display_name']


admin.site.register(Player, PlayerAdmin)


class SeasonAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_default', 'pub_date')
    actions = ['set_default_season', 'update_stats', 'expire_caches']

    def expire_caches(self, request, _):  # noqa
        expire_caches()
        self.message_user(
            request,
            level='INFO',
            message='Caches expired.',
        )
        return redirect(request.get_full_path())

    def set_default_season(self, request, queryset):
        # queryset should be 1 season
        if len(queryset) == 1:
            # make sure all the other seasons aren't the default
            for a_season in Season.objects.all().exclude(id__in=[queryset[0].id]):
                a_season.is_default = False
                a_season.save()
            queryset[0].is_default = True
            queryset[0].save()
            self.message_user(
                request,
                level='INFO',
                message='{} is now the default season.'.format(queryset[0])
            )
        else:
            self.message_user(
                request,
                level='ERROR',
                message='You must select exactly one season to be the default.',
            )
            return False

    def update_stats(self, request, queryset):
        # We need to redirect to this path later, because when we want to expire the cache,
        # we have to change the path of the request object, resulting in a redirect to the player page
        # of the last object expired, which is confusing. We can't copy.deepcopy() the request object,
        # due to a "TypeError: cannot serialize '_io.BufferedReader' object" error.
        redirect_to = request.get_full_path()
        if len(queryset) == 1:
            season_id = queryset[0].id
            update_season_stats(season_id)
            expire_caches()
            self.message_user(
                request,
                level='INFO',
                message='Stats updated and caches expired.',
            )
        else:
            self.message_user(
                request,
                level='ERROR',
                message='You must select exactly one season to update stats for.',
            )
        # see comment about redirect_to above
        return redirect(redirect_to)


admin.site.register(Season, SeasonAdmin)
admin.site.register(Sponsor)


class WeekDivisionMatchupInline(admin.StackedInline):
    model = WeekDivisionMatchup
    extra = 0


class WeekAdmin(admin.ModelAdmin):
    list_filter = ['season']
    list_display = ['name', 'season', 'date']
    actions = ['division_matchups', 'intra_division_matches', 'league_rank_matches', 'lint_table_assignments']
    inlines = [WeekDivisionMatchupInline]

    def get_form(self, request, obj=None, **kwargs):
        form = super(WeekAdmin, self).get_form(request, obj, **kwargs)
        form.base_fields['season'].initial = get_default_season()
        return form

    @staticmethod
    def find_unscheduled_teams(week):
        # get all the teams in the season
        season_teams = set(Team.objects.filter(season=week.season))
        matches = Match.objects.filter(week=week)
        for match in matches:
            season_teams.discard(match.home_team)
            season_teams.discard(match.away_team)
        return season_teams

    def lint_table_assignments(self, request, queryset):
        # queryset should be 1 week
        if len(queryset) == 1:  # and type(queryset[0], 'Week'):
            unscheduled_teams = self.find_unscheduled_teams(week=queryset[0])
            if len(unscheduled_teams):
                self.message_user(
                    request,
                    level='WARNING',
                    message="there are unscheduled teams: {ts}".format(ts=', '.join([t.name for t in unscheduled_teams]))
                )
            find_duplicate_table_assignments(self, request, queryset[0])
        else:
            self.message_user(
                request,
                level='ERROR',
                message='you must select exactly one week to lint table assignments',
            )
            return False

    def check_matchup_length(self, request, week):
        division_matchups = WeekDivisionMatchup.objects.filter(week=week)
        div_matchup_count = int(len(Division.objects.filter(season_id=week.season))/2)
        if len(division_matchups) != div_matchup_count:
            self.message_user(
                request,
                'the week must have exactly {} division matchups set'.format(div_matchup_count),
                level='ERROR',
            )
            return False
        else:
            return True

    def check_ties(self, request, teams):
        ties = []
        for i in range(0, len(teams) - 1):
            if teams[i].ranking == teams[i+1].ranking:
                ties.append((teams[i], teams[i+1]))
        if len(ties):
            # print('ties are: {}'.format(ties))
            for tie in ties:
                self.message_user(
                    request,
                    '{} and {} are tied, no matches created.'.format(tie[0], tie[1]),
                    level='ERROR'
                )
            return True
        else:
            return False

    def create_match_if_not_exist(self, week, request, away_team, home_team):
        existing_matches = Match.objects.filter(week=week).filter(
                away_team=away_team).filter(home_team=home_team)
        if len(existing_matches):
            for m in existing_matches:
                self.message_user(
                    request,
                    'match {} in week {} exists, skipping '.format(m, week)
                )
        else:
            m = Match(
                week=week,
                away_team=away_team,
                home_team=home_team,
                season=week.season,
            )
            m.save()
            self.message_user(request, 'created match {}'.format(m))

    def set_matches_for_division_matchup(self, request, _week, division_matchup):
        away_teams = Team.objects.filter(
            division=division_matchup.away_division
        ).filter(season=_week.season).order_by('ranking')
        home_teams = Team.objects.filter(
            division=division_matchup.home_division
        ).filter(season=_week.season).order_by('ranking')
        for i in range(0, min(len(away_teams), len(home_teams))):
            self.create_match_if_not_exist(_week, request, away_team=away_teams[i], home_team=home_teams[i])

        if len(away_teams) != len(home_teams):
            self.message_user(
                request,
                level='WARNING',
                message='divisions {} and {} are uneven, {} and {} teams; manual matches needed'.format(
                    division_matchup.away_division,
                    division_matchup.home_division,
                    len(away_teams), len(home_teams)),
            )

    def division_matchups(self, request, queryset):

        # check that we are working on exactly one week
        if len(queryset) != 1:
            self.message_user(request=request, message='must select exactly one week', level='ERROR')
            return
        _week = queryset[0]

        # check that the one week has the right number of matchups set. is this necessary? or just check for over?
        if self.check_matchup_length(request, _week):
            pass
        else:
            return
        tied_divisions = 0
        for division in Division.objects.filter(season=_week.season):
            teams = Team.objects.filter(division=division).order_by('ranking')
            ties = Team.find_ties(teams, 'ranking')
            for tie in ties:
                self.message_user(
                    request=request,
                    message='{} are tied; no matches set'.format(', '.join([t.name for t in tie.teams.all()])),
                    level='ERROR',
                )
                return
        if tied_divisions:
            return
        division_matchups = WeekDivisionMatchup.objects.filter(week=_week)
        for division_matchup in division_matchups:
            self.set_matches_for_division_matchup(request, _week, division_matchup)

    division_matchups.short_description = "Set inter-division ranked matches"

    def league_rank_matches(self, request, queryset):
        if len(queryset) != 1:
            self.message_user(request=request, message='must select exactly one week', level='ERROR')
            return
        _week = queryset[0]
        print("week is : {}".format(_week))
        # is this a div-ranked week?
        division_matchups = WeekDivisionMatchup.objects.filter(week=_week)
        if len(division_matchups):
            self.message_user(
                request=request,
                message='This week has division matchups set! not setting league-ranked matches.',
                level='ERROR',
            )
        # check for ties
        teams = Team.objects.filter(season=_week.season).order_by('ranking')
        ties = Team.find_ties(teams, 'ranking')
        for tie in ties:
            self.message_user(
                request=request,
                message='{} are tied; no matches set'.format(', '.join([team.name for team in tie.teams.all()])),
                level='ERROR'
            )
            return
        # so there are no ties ... set matches!
        inc = 0
        while inc < len(teams):
            self.create_match_if_not_exist(_week, request, away_team=teams[inc + 1], home_team=teams[inc])
            inc += 2

    league_rank_matches.short_description = "Set league-ranked matches"

    def intra_division_matches(self, request, queryset):
        if len(queryset) != 1:
            self.message_user(request=request, message='must select exactly one week', level='ERROR')
            return
        _week = queryset[0]
        divisions = Division.objects.filter(season=_week.season)
        for division in divisions:
            div_teams = Team.objects.filter(division=division).order_by('ranking')
            if len(div_teams) % 2:
                self.message_user(request,
                                  message="{d} has an uneven team count, no match created for {t}".format(
                                      d=division, t=div_teams[len(div_teams)-1]),
                                  level='WARNING'
                                  )
            div_ties = Team.find_ties(div_teams, 'division_ranking')
            if div_ties:
                self.message_user(
                    request,
                    message="{} and {} are tied; no matches created for {}",
                    level='ERROR',
                )
                continue
            inc = 0
            match_count = int((len(div_teams) - (len(div_teams) % 2)) / 2)
            print("we should create {} matches in division {}".format(match_count, division))
            while inc < match_count:
                self.create_match_if_not_exist(_week, request,
                                               away_team=div_teams[2 * inc + 1],
                                               home_team=div_teams[2 * inc]
                                               )
                inc += 1

    intra_division_matches.short_description = "Set intra-division ranked matches"


admin.site.register(Week, WeekAdmin)


class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'record', 'season', 'ranking', 'forfeit_wins', 'rank_tie_breaker', 'division')
    list_filter = [SeasonFilter, 'rank_tie_breaker']
    filter_horizontal = ['players']
    fields = ['season', 'table', 'division', 'name', 'captain', 'players', 'rank_tie_breaker']
    actions = ['clear_tie_breakers', 'add_tie_breakers', 'detect_ties']
    save_as = True

    form = TeamForm

    @staticmethod
    def record(obj):
        return mark_safe(format_html('<a href="{}">view</a>'.format(reverse('team', args=(obj.id,)))))

    def clear_tie_breakers(self, request, queryset):

        for team in queryset:
            team.rank_tie_breaker = 0
            team.save()

    clear_tie_breakers.short_description = "Clear tie-breakers"

    def add_tie_breakers(self, request, queryset):

        for team in queryset:
            old_value = team.rank_tie_breaker
            team.rank_tie_breaker = old_value + 1
            team.save()

    add_tie_breakers.short_description = "Add 1 to tie-breaker"

    def detect_ties(self, request, queryset):

        ties = Team.find_ties(queryset, 'ranking')
        if len(ties):
            for tie in ties:
                self.message_user(
                    request=request,
                    message='{} are tied.'.format(', '.join([t.name for t in tie.teams.all()])),
                    level='WARNING'
                )
        else:
            self.message_user(
                request=request,
                message='No ties detected.',
                level='INFO',
            )

    detect_ties.short_description = "Detect ties"


admin.site.register(Team, TeamAdmin)


class ScoreAdjustmentAdmin(admin.ModelAdmin):

    fields = ['team', 'wins', 'losses', 'description']
    form = ScoreAdjustmentAdminForm


admin.site.register(ScoreAdjustment, ScoreAdjustmentAdmin)


class PlayPositionAdmin(admin.ModelAdmin):
    list_display = ('name', 'home_name', 'away_name')


admin.site.register(PlayPosition, PlayPositionAdmin)


def make_official(modeladmin, request, queryset):
    queryset.update(official=1)


def lint_score_sheets(modeladmin, request, queryset):

    for score_sheet in queryset:
        warnings = score_sheet.self_check(mark_for_review=True)
        if len(warnings):
            score_sheet.official = 2
            score_sheet.save()
        for warning in warnings:
            modeladmin.message_user(
                request=request,
                message="{}/{}: {}".format(score_sheet, score_sheet.id, warning),
                level='WARNING'
            )


class BlankScoreSheetFilter(admin.SimpleListFilter):
    title = _('no wins')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'is_blank'

    def lookups(self, request, model_admin):
        return (
            ('blank', _('no wins')),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value (either '80s' or '90s')
        # to decide how to filter the queryset.
        # return queryset.filter(birthday__gte=date(1990, 1, 1),)
        if self.value() == 'blank':
            blank = []
            for s in queryset:
                if s.away_wins() == 0 and s.home_wins() == 0:
                    blank.append(s.id)
            return ScoreSheet.objects.filter(id__in=blank)
        else:
            return queryset


class ScoreSheetAdmin(admin.ModelAdmin):
    list_display = ['id', 'match', 'links', 'away_wins', 'home_wins', 'official', 'complete', 'comment']
    fields = ['official', 'complete', 'comment']
    list_filter = [MatchSeasonFilter, 'official', 'complete', BlankScoreSheetFilter, 'match__week']
    actions = [lint_score_sheets, make_official, 'update_stats']

    @staticmethod
    def opponents(obj):
        return "{} @ {}".format(obj.match.away_team, obj.match.home_team)

    @staticmethod
    def links(obj):
        score_sheet_links = format_html('<a href="{}">view</a>'.format(reverse('score_sheet', args=(obj.id,))))
        return mark_safe(score_sheet_links)

    def update_stats(self, request, queryset):
        # We need to redirect to this path later, because when we want to expire the cache,
        # we have to change the path of the request object, resulting in a redirect to the player page
        # of the last player updated, which is confusing. We can't copy.deepcopy() the request object,
        # due to a "TypeError: cannot serialize '_io.BufferedReader' object" error.
        redirect_to = request.get_full_path()
        # we'll assume the season is the same for all the score sheets and use the first one
        update_season_id = queryset[0].match.season.id
        if len(queryset) == 1:
            update_season_stats(update_season_id)
            expire_caches()
            self.message_user(
                request,
                level='INFO',
                message='Stats updated and caches expired.',
            )
        else:
            self.message_user(
                request,
                level='ERROR',
                message='You must select exactly one score sheet to update stats for.',
            )
        # see comment about redirect_to above
        return redirect(redirect_to)


admin.site.register(ScoreSheet, ScoreSheetAdmin)


class GameOrderAdmin(admin.ModelAdmin):
    list_display = ['order', 'away_position', 'home_position', 'home_breaks']


admin.site.register(GameOrder, GameOrderAdmin)


class MatchAdmin(admin.ModelAdmin):
    list_filter = ['week', SeasonFilter, 'playoff']
    list_display = ['id', 'away_team', 'home_team', 'week', 'table']
    actions = ['lint_table_assignments']

    form = MatchForm

    def lint_table_assignments(self, request, queryset):
        # we'll just use the week from the first match
        if len(queryset) < 1:  # or not type(queryset[0], 'Match'):
            self.message_user(
                request,
                level='ERROR',
                message='you must select a match to check table assignments for it\'s week of play',
            )
            return False
        find_duplicate_table_assignments(self, request, queryset[0].week)

    def get_changeform_initial_data(self, request):
        try:
            # default_season = Season.objects.filter(is_default=True)[0]
            default_season = Season.objects.get(is_default=True)
            return {'season': default_season.id}
        except Season.DoesNotExist as e:
            return {}


admin.site.register(Match, MatchAdmin)


class TableAdmin(admin.ModelAdmin):
    pass


admin.site.register(Table, TableAdmin)


# TODO:
# It would be pretty to have, in the match admin, the teams filtered by season
# formfield_for_foreignkey seems to be the way to go?
# class MatchAdmin(admin.ModelAdmin):
#     list_filter = ['season', 'week']
#
#     # def formfield_for_foreignkey(db_field, request, **kwargs):
#     # def formfield_for_foreignkey(self, db_field, request, **kwargs):
#     def formfield_for_foreignkey(self, db_field, request, **kwargs):
#         if db_field.name == "team":
#             kwargs["queryset"] = Team.objects.filter(owner=request.session['season_id'])
#         return super(MatchAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

# admin.site.register(Match, MatchAdmin)
# this is done in the model at the moment, by setting limit_choices_to with a Q queryset; this works
# but only teams from the default season are available in the admin
