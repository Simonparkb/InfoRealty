from django.urls import path
from . import views
from .views import kakaomap, index

urlpatterns = [
    path('', index, name='index'),
    path('infoRealty/', kakaomap, name='kakaomap'),
    path('find_shortest_route/', views.find_shortest_route, name='find_shortest_route')
]