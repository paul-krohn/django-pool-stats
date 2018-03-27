from django.contrib import admin
from django.urls import reverse
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils.html import format_html
from django.contrib.admin import SimpleListFilter

from .models import Division, GameOrder, Match, Player, PlayPosition, ScoreSheet, Season, Sponsor, Team, Week

from .forms import MatchForm

admin.AdminSite.site_header = "{} stats admin".format(settings.LEAGUE['name'])


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

    # TODO: make this require less repeated code just to make
    # model_path__is_default vary
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


class WeekAdmin(admin.ModelAdmin):
    list_filter = ['season']
    list_display = ['name', 'season', 'date']


admin.site.register(Week, WeekAdmin)


class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'season', 'ranking', 'rank_tie_breaker')
    list_filter = [SeasonFilter, 'rank_tie_breaker']
    filter_horizontal = ['players']
    fields = ['season', 'sponsor', 'division', 'name', 'players', 'rank_tie_breaker']
    save_as = True


admin.site.register(Team, TeamAdmin)


class PlayPositionAdmin(admin.ModelAdmin):
    list_display = ('name', 'home_name', 'away_name')


admin.site.register(PlayPosition, PlayPositionAdmin)


def make_official(modeladmin, request, queryset):
    queryset.update(official=True)
make_official.description = "Mark selected score sheets as official"


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
    list_display = ['opponents', 'links', 'away_wins', 'home_wins', 'official', 'complete', 'comment']
    fields = ['official', 'complete', 'comment']
    list_filter = [MatchSeasonFilter, 'official', 'complete', BlankScoreSheetFilter, 'match__week']
    actions = [make_official]

    @staticmethod
    def opponents(obj):
        return "{} @ {}".format(obj.match.away_team, obj.match.home_team)

    def links(self, obj):
        edit_url = reverse('score_sheet_edit', args=(obj.id,))
        view_url = reverse('score_sheet', args=(obj.id,))
        return format_html('<a href="{}">edit</a>/<a href="{}">view</a>'.format(edit_url, view_url))

    links.allow_tags = True


admin.site.register(ScoreSheet, ScoreSheetAdmin)


class GameOrderAdmin(admin.ModelAdmin):
    list_display = ['order', 'away_position', 'home_position', 'home_breaks']


admin.site.register(GameOrder, GameOrderAdmin)


class MatchAdmin(admin.ModelAdmin):
    list_filter = ['week', SeasonFilter, 'playoff']
    list_display = ['id', 'away_team', 'home_team', 'week']

    form = MatchForm

    def get_changeform_initial_data(self, request):
        try:
            default_season = Season.objects.filter(is_default=True)[0]
            return {'season': default_season.id}
        except ValueError:
            return {}


admin.site.register(Match, MatchAdmin)


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
