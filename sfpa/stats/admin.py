from django.contrib import admin

from .models import Division, Player, Season, Team, Sponsor

admin.site.register(Division)
admin.site.register(Player)
admin.site.register(Season)
admin.site.register(Sponsor)


class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'season')
    list_filter = ['season']
    filter_horizontal = ['players']

admin.site.register(Team, TeamAdmin)
