from django.contrib import admin
from django.urls import reverse
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.contrib.admin import SimpleListFilter
from django.shortcuts import redirect

from .models import Division, GameOrder, Match, Player, PlayPosition, WeekDivisionMatchup
from .models import PlayerSeasonSummary, ScoreSheet, Season, Sponsor, Table, Team, Week
from .forms import MatchForm
from .utils import expire_page

admin.AdminSite.site_header = "{} stats admin".format(settings.LEAGUE['name'])


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

    def get_queryset(self, request):
        qs = super(DivisionAdmin, self).get_queryset(request)
        if 'season_id' in request.session.keys():
            return qs.filter(season=request.session['season_id'])
        else:
            return qs


admin.site.register(Division, DivisionAdmin)


class PlayerAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'last_name', 'first_name', 'email']
    search_fields = ['last_name', 'first_name', 'display_name']


admin.site.register(Player, PlayerAdmin)


class SeasonAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_default', 'pub_date')


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

    def lint_table_assignments(self, request, queryset):
        # queryset should be 1 week
        if len(queryset) == 1:  # and type(queryset[0], 'Week'):
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

    def check_division_ties(self, request, division):
        teams = Team.objects.filter(division=division).order_by('-ranking')
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
        if len(away_teams) == len(home_teams):
            for i in range(0, len(away_teams)):
                self.create_match_if_not_exist(_week, request, away_team=away_teams[i], home_team=home_teams[i])

        else:
            print('divisions are uneven: away teams: {} and home teams: {}'.format(away_teams, home_teams))

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
            if self.check_division_ties(request, division):
                tied_divisions += 1
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
                message='{} and {} are tied; no matches set'.format(tie[0], tie[1]),
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
            div_teams = Team.objects.filter(division=division)
            if len(div_teams) % 2:
                self.message_user(request,
                                  message="{} has an uneven team count, no matches created".format(division),
                                  level='ERROR'
                                  )
                self.message_user(request,
                                  message="teams are: {}".format(div_teams),
                                  level='ERROR'
                                  )
                continue
            div_ties = Team.find_ties(div_teams, 'division_ranking')
            if div_ties:
                self.message_user(
                    request,
                    message="{} and {} are tied; no matches created for {}",
                    level='ERROR',
                )
                continue
            inc = 0
            while inc + 1 < len(div_teams):
                self.create_match_if_not_exist(_week, request, away_team=div_teams[inc+1], home_team=div_teams[inc])
                inc += 2

    intra_division_matches.short_description = "Set intra-division ranked matches"


admin.site.register(Week, WeekAdmin)


class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'record', 'season', 'ranking', 'forfeit_wins', 'rank_tie_breaker')
    list_filter = [SeasonFilter, 'rank_tie_breaker']
    filter_horizontal = ['players']
    fields = ['season', 'table', 'division', 'name', 'players', 'rank_tie_breaker']
    actions = ['clear_tie_breakers', 'add_tie_breakers']
    save_as = True

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


admin.site.register(Team, TeamAdmin)


class PlayPositionAdmin(admin.ModelAdmin):
    list_display = ('name', 'home_name', 'away_name')


admin.site.register(PlayPosition, PlayPositionAdmin)


def make_official(modeladmin, request, queryset):
    queryset.update(official=1)


def update_stats(modeladmin, request, queryset):
    # We need to redirect to this path later, because when we want to expire the cache,
    # we have to change the path of the request object, resulting in a redirect to the player page
    # of the last player updated, which is confusing. We can't copy.deepcopy() the request object,
    # due to a "TypeError: cannot serialize '_io.BufferedReader' object" error.
    redirect_to = request.get_full_path()
    # we'll assume the season is the same for all the score sheets and use the first one
    expire_season_id = queryset[0].match.season.id
    for score_sheet in queryset:
        for team in [score_sheet.match.home_team, score_sheet.match.away_team]:
            team.count_games()
            expire_page(request, reverse('team', kwargs={'team_id': team.id}), '')
    PlayerSeasonSummary.update_all(season_id=expire_season_id)
    for pss in PlayerSeasonSummary.objects.filter(season_id=expire_season_id):
        expire_page(request, reverse('player', kwargs={'player_id': pss.player.id}))
    Team.update_rankings(season_id=expire_season_id)
    expire_page(request, reverse('divisions', kwargs={'season_id': expire_season_id}), '')
    expire_page(request, reverse('players', kwargs={'season_id': expire_season_id}), '')
    expire_page(request, reverse('teams', kwargs={'season_id': expire_season_id}), '')
    # see comment about redirect_to above
    return redirect(redirect_to)


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
    actions = [lint_score_sheets, make_official, update_stats]

    @staticmethod
    def opponents(obj):
        return "{} @ {}".format(obj.match.away_team, obj.match.home_team)

    @staticmethod
    def links(obj):
        score_sheet_links = format_html('<a href="{}">view</a>'.format(reverse('score_sheet', args=(obj.id,))))
        if obj.official != 1:
            score_sheet_links += '/' + format_html('<a href="{}">edit</a>'.format(
                reverse('score_sheet_edit', args=(obj.id,))))
        return mark_safe(score_sheet_links)


admin.site.register(ScoreSheet, ScoreSheetAdmin)


class GameOrderAdmin(admin.ModelAdmin):
    list_display = ['order', 'away_position', 'home_position', 'home_breaks']


admin.site.register(GameOrder, GameOrderAdmin)


class MatchAdmin(admin.ModelAdmin):
    list_filter = ['week', SeasonFilter, 'playoff']
    list_display = ['id', 'away_team', 'home_team', 'week']
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
            default_season = Season.objects.filter(is_default=True)[0]
            return {'season': default_season.id}
        except ValueError:
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
