from django.urls import path
from . import views
from .views import kakaomap, departures, arrivals, services,station_map,station_detail,add_station,delete_station,get_line_images

urlpatterns = [
    path('', departures, name='departures'),
    path('B/', arrivals, name='arrivals'),
    path('C/', services, name='services'),
    path('infoRealty/', kakaomap, name='kakaomap'),
    path('find_shortest_route/', views.find_shortest_route, name='find_shortest_route'),
    path('find_nearest_stations/', views.find_nearest_stations, name='find_nearest_stations'),
    path('edit_map/', views.station_map, name='station_map'),
    path('stations/<str:station_name>/<str:station_line>/', views.station_detail, name='station_detail'),
    path('stations/add/', views.add_station, name='add_station'),  # Add station URL pattern
    path('stations/delete/<str:station_name>/<str:station_line>/', views.delete_station, name='delete_station'),
    path('get_line_images/', views.get_line_images, name='get_line_images'),
    path('stations/add_new_line/', views.add_new_line, name='add_new_line'),
]
