
from django.contrib.auth.models import User
from django.db import models
import datetime
class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.action} at {self.timestamp}"

class Station(models.Model):
    line = models.CharField(max_length=100)  # 노선 이름
    name = models.CharField(max_length=100)  # 역 이름
    latitude = models.FloatField()  # 위도
    longitude = models.FloatField()  # 경도
    sort_order = models.IntegerField()  # 정렬 순서 (역 순서 관리)
    is_transfer = models.BooleanField(default=False)  # 환승역 여부, 기본값은 False
    branch_ids = models.JSONField(default=list, blank=True)  # 여러 분기 ID를 JSON 배열로 저장
    is_branch_point = models.BooleanField(default=False)  # 분기점 여부, 기본값은 False
    opening_date = models.DateField(default=datetime.date(1900, 1, 1), null=True, blank=True)  # 개통일, 기본값 1900-01-01
    description = models.CharField(max_length=200, blank=True, default="현재 역정보를 입력해주세요!")  # 200자 이하 설명란

    def __str__(self):
        return f"{self.line} - {self.name}"
    def __str__(self):
        return f"{self.line} - {self.name}"