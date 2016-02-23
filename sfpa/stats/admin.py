from django.contrib import admin

from .models import Division, Match, Player, Season, Sponsor, Team, Week

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
