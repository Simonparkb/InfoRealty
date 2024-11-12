from django import forms
from django.contrib import admin
from django.db import transaction
from .models import Station, ActivityLog


@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = (
        'line', 'name', 'latitude', 'longitude', 'sort_order', 'is_transfer',
        'is_branch_point', 'opening_date', 'description'
    )
    list_filter = ('line', 'is_transfer', 'is_branch_point')
    actions = ['reset_sort_order_action']

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "description":
            kwargs["widget"] = forms.TextInput(attrs={"placeholder": "현재 역정보를 입력해주세요"})
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    @transaction.atomic
    def reset_sort_order_action(self, request, queryset):
        lines = Station.objects.values_list('line', flat=True).distinct()
        for line in lines:
            stations = Station.objects.filter(line=line).order_by('sort_order')
            for i, station in enumerate(stations, start=1):
                station.sort_order = i
                station.save()
        self.message_user(request, "Sort order reset successfully by line and sorted order.")


# ActivityLog 모델을 Django Admin에 등록
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'timestamp')
    search_fields = ('user__username', 'action')
    list_filter = ('user', 'timestamp')

admin.site.register(ActivityLog, ActivityLogAdmin)