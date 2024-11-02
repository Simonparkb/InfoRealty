from django.contrib import admin
from django.db import transaction
from django.db.models import F
from .models import Station, ActivityLog

@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = ('line', 'name', 'latitude', 'longitude', 'sort_order', 'is_transfer')  # is_transfer 추가
    list_filter = ('line', 'is_transfer')  # 필터에 is_transfer 추가
    actions = ['reset_sort_order_action']  # 상단 액션 메뉴에 추가

    @transaction.atomic
    def reset_sort_order_action(self, request, queryset):
        # 모든 노선을 distinct()로 가져와 각 노선을 별도로 처리
        lines = Station.objects.values_list('line', flat=True).distinct()

        for line in lines:
            # 해당 노선의 역들을 기존 sort_order 순으로 정렬하여 가져옴
            stations = Station.objects.filter(line=line).order_by('sort_order')

            # 노선 내에서 1부터 순차적으로 sort_order 재부여
            for i, station in enumerate(stations, start=1):
                station.sort_order = i
                station.save()

        # 성공 메시지 출력
        self.message_user(request, "Sort order reset successfully by line and sorted order.")

# ActivityLog 모델을 Django Admin에 등록
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'timestamp')
    search_fields = ('user__username', 'action')
    list_filter = ('user', 'timestamp')


admin.site.register(ActivityLog, ActivityLogAdmin)