from django.contrib import admin

from .models import Season, Team, Sponsor

admin.site.register(Season)
admin.site.register(Sponsor)


class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'season')
    list_filter = ['season']

admin.site.register(Team, TeamAdmin)
