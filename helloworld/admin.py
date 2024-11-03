from django import forms
from django.contrib import admin
from django.db import transaction
from .models import Station, ActivityLog


# 커스텀 필터 클래스 정의
class BranchIdListFilter(admin.SimpleListFilter):
    title = 'Branch ID'
    parameter_name = 'branch_id'

    def lookups(self, request, model_admin):
        branch_ids = Station.objects.values_list('branch_ids', flat=True)
        unique_ids = set()
        for ids in branch_ids:
            if ids:
                unique_ids.update(ids)
        return [(id, f'Branch ID {id}') for id in unique_ids if id is not None]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(branch_ids__contains=[int(self.value())])
        return queryset

# StationAdmin 정의
@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = (
        'line', 'name', 'latitude', 'longitude', 'sort_order', 'is_transfer', 'branch_ids_display',
        'is_branch_point', 'opening_date', 'description'
    )
    list_filter = ('line', 'is_transfer', BranchIdListFilter, 'is_branch_point')
    actions = ['reset_sort_order_action']

    # formfield_for_dbfield를 사용하여 branch_ids 입력을 쉼표로 구분된 문자열로 변환
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "branch_ids":
            kwargs["widget"] = forms.TextInput(attrs={"placeholder": "예: 2,3,4"})
            kwargs["initial"] = ""  # 빈 문자열을 기본값으로 설정하여 []를 표시하지 않음
        if db_field.name == "description":
            kwargs["widget"] = forms.TextInput(attrs={"placeholder": "현재 역정보를 입력해주세요"})  # 기본값에 맞춘 설명 입력란

        form_field = super().formfield_for_dbfield(db_field, request, **kwargs)

        # 입력된 쉼표 구분 문자열을 JSON 배열로 변환
        if db_field.name == "branch_ids":
            original_clean = form_field.clean

            def clean(value):
                if value:
                    # 쉼표로 구분된 문자열을 JSON 배열로 변환
                    return [int(v.strip()) for v in value.split(",") if v.strip()]
                return []  # 빈 입력 시 빈 리스트 반환

            form_field.clean = clean
        return form_field

    @transaction.atomic
    def reset_sort_order_action(self, request, queryset):
        lines = Station.objects.values_list('line', flat=True).distinct()
        for line in lines:
            stations = Station.objects.filter(line=line).order_by('sort_order')
            for i, station in enumerate(stations, start=1):
                station.sort_order = i
                station.save()
        self.message_user(request, "Sort order reset successfully by line and sorted order.")

    def branch_ids_display(self, obj):
        return ", ".join(map(str, obj.branch_ids))

    branch_ids_display.short_description = "Branch IDs"

# ActivityLog 모델을 Django Admin에 등록
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'timestamp')
    search_fields = ('user__username', 'action')
    list_filter = ('user', 'timestamp')

admin.site.register(ActivityLog, ActivityLogAdmin)