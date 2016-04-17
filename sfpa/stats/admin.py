from django.contrib import admin

from .models import Division, GameOrder, Match, Player, PlayPosition, ScoreSheet, Season, Sponsor, Team, Week


admin.AdminSite.site_header = "SFPA stats admin"


admin.site.register(Division)
admin.site.register(Match)
admin.site.register(Player)
admin.site.register(Season)
admin.site.register(Sponsor)
admin.site.register(Week)


class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'season')
    list_filter = ['season']
    filter_horizontal = ['players']

admin.site.register(Team, TeamAdmin)


class PlayPositionAdmin(admin.ModelAdmin):
    list_display = ('name', 'home_name', 'away_name')

admin.site.register(PlayPosition, PlayPositionAdmin)


class ScoreSheetAdmin(admin.ModelAdmin):
    list_display = ['match', 'official']
    fields = ['official']
    list_filter = ['official']

admin.site.register(ScoreSheet, ScoreSheetAdmin)


class GameOrderAdmin(admin.ModelAdmin):
    list_display = ['name', 'away_position', 'home_position', 'home_breaks']

admin.site.register(GameOrder, GameOrderAdmin)


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
