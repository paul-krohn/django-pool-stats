from django.contrib import admin
from django.core.urlresolvers import reverse

from .models import Division, GameOrder, Match, Player, PlayPosition, ScoreSheet, Season, Sponsor, Team, Week


admin.AdminSite.site_header = "SFPA stats admin"


class DivisionAdmin(admin.ModelAdmin):
    list_filter = ['season']

admin.site.register(Division, DivisionAdmin)

admin.site.register(Player)
admin.site.register(Season)
admin.site.register(Sponsor)


class WeekAdmin(admin.ModelAdmin):
    list_filter = ['season']

admin.site.register(Week, WeekAdmin)


class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'season', 'ranking', 'rank_tie_breaker')
    list_filter = ['season', 'rank_tie_breaker']
    filter_horizontal = ['players']
    fields = ['season', 'sponsor', 'division', 'name', 'players', 'rank_tie_breaker']
    save_as = True


admin.site.register(Team, TeamAdmin)


class PlayPositionAdmin(admin.ModelAdmin):
    list_display = ('name', 'home_name', 'away_name')

admin.site.register(PlayPosition, PlayPositionAdmin)


class ScoreSheetAdmin(admin.ModelAdmin):
    list_display = ['opponents', 'links', 'away_wins', 'home_wins', 'official', 'complete', 'comment']
    fields = ['official', 'complete', 'comment']
    list_filter = ['official', 'complete', 'match__season']

    @staticmethod
    def opponents(obj):
        return "{} @ {}".format(obj.match.away_team, obj.match.home_team)

    def links(self, obj):
        edit_url = reverse('score_sheet_edit', args=(obj.id,))
        view_url = reverse('score_sheet', args=(obj.id,))
        return '<a href="{}">edit</a>/<a href="{}">view</a>'.format(edit_url, view_url)

    links.allow_tags = True

admin.site.register(ScoreSheet, ScoreSheetAdmin)


class GameOrderAdmin(admin.ModelAdmin):
    list_display = ['name', 'away_position', 'home_position', 'home_breaks']

admin.site.register(GameOrder, GameOrderAdmin)


class MatchAdmin(admin.ModelAdmin):
    list_filter = ['season', 'playoff']

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
