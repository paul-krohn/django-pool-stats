from django.contrib import admin

from .models import Season, Team

admin.site.register(Season)


class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'season')
    list_filter = ['season']

admin.site.register(Team, TeamAdmin)
