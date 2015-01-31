from __future__ import unicode_literals

from django.contrib import admin
from .models import SavedQuery


class SavedQueryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created', 'created_by', 'last_run')
    list_filter = ('created_by',)
    search_fields = ('name',)
    ordering = ('-last_run',)


admin.site.register(SavedQuery, SavedQueryAdmin)
