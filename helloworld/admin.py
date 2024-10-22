from django.contrib import admin
from .models import ActivityLog
from helloworld.models import Station

from django.contrib import admin
from .models import Station
from django.db.models import F

from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Station
from django.db.models import F

from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.shortcuts import redirect  # redirect 함수 임포트
from .models import Station
from django.db.models import F


@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = ('line', 'name', 'latitude', 'longitude', 'sort_order', 'move_up', 'move_down')

    def move_up(self, obj):
        return mark_safe(f'<a href="{reverse("admin:station_move_up", args=[obj.pk])}">Up</a>')

    def move_down(self, obj):
        return mark_safe(f'<a href="{reverse("admin:station_move_down", args=[obj.pk])}">Down</a>')

    move_up.short_description = 'Move Up'
    move_down.short_description = 'Move Down'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<int:station_id>/move_up/', self.admin_site.admin_view(self.move_up_view), name='station_move_up'),
            path('<int:station_id>/move_down/', self.admin_site.admin_view(self.move_down_view),
                 name='station_move_down'),
        ]
        return custom_urls + urls

    def move_up_view(self, request, station_id):
        station = Station.objects.get(pk=station_id)
        if station.sort_order > 1:
            Station.objects.filter(sort_order=station.sort_order - 1).update(sort_order=F('sort_order') + 1)
            station.sort_order -= 1
            station.save()
        return redirect(request.META.get('HTTP_REFERER'))  # 이동 후 다시 목록으로 리다이렉트

    def move_down_view(self, request, station_id):
        station = Station.objects.get(pk=station_id)
        next_station = Station.objects.filter(sort_order=station.sort_order + 1).first()
        if next_station:
            next_station.sort_order -= 1
            next_station.save()
            station.sort_order += 1
            station.save()
        return redirect(request.META.get('HTTP_REFERER'))  # 이동 후 다시 목록으로 리다이렉트


# ActivityLog 모델을 Django Admin에 등록
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'timestamp')
    search_fields = ('user__username', 'action')
    list_filter = ('user', 'timestamp')

admin.site.register(ActivityLog, ActivityLogAdmin)