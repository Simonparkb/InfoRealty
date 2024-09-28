from django.contrib import admin
from .models import ActivityLog


class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'timestamp')
    search_fields = ('user__username', 'action')
    list_filter = ('user', 'timestamp')


admin.site.register(ActivityLog, ActivityLogAdmin)
