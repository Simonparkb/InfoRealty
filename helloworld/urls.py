from django.urls import path
from . import views
from .views import kakaomap, departures, arrivals, services

urlpatterns = [
    path('', departures, name='departures'),
    path('arrivals/', arrivals, name='arrivals'),
    path('services/', services, name='services'),
    path('infoRealty/', kakaomap, name='kakaomap'),
    path('find_shortest_route/', views.find_shortest_route, name='find_shortest_route'),
    path('find_nearest_stations/', views.find_nearest_stations, name='find_nearest_stations')
]