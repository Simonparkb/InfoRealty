
from django.contrib.auth.models import User
from django.db import models

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

    def __str__(self):
        return f"{self.line} - {self.name}"