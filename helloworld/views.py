from .models import ActivityLog
import math
import csv
import os
import json
from collections import defaultdict
from django.shortcuts import render
import pandas as pd
import networkx as nx
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

# view.py
from django.http import JsonResponse
from math import radians, cos, sin, sqrt, atan2

load_stations_from_csv = []

def index(request):
    return render(request, 'index.html')

def log_activity(user, action):
    ActivityLog.objects.create(user=user, action=action)

def kakaomap(request):
    return render(request, 'kakao.html', {'stations': load_stations_from_csv()})

# Helper functions to load stations and build the graph
def load_stations_from_csv():
    csv_file_path = os.path.join(settings.BASE_DIR, 'data', 'rawdata.csv')

    stations = []
    station_map = defaultdict(list)

    with open(csv_file_path, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            station_info = {
                'name': row['name'],
                'line': row['line'],
                'latitude': float(row['Latitude']),
                'longitude': float(row['Longitude']),
                'transfer': row['환승'] == 'TRUE'
            }
            station_map[row['name']].append(station_info)

    for station_name, station_list in station_map.items():
        lines = set([station['line'] for station in station_list])
        if len(lines) > 1:
            for station in station_list:
                station['transfer'] = True
        stations.extend(station_list)
    return stations

# CSV 파일에서 그래프를 생성하는 함수
def build_graph_from_csv():
    # CSV 파일 경로 설정
    # csv_file_path = os.path.join(settings.BASE_DIR,
    #                              'C:\\Users\\parkk\\PycharmProjects\\infoRealty\\myDjango\\data',
    #                              '1rawdata_shortest.csv')
    csv_file_path = os.path.join(settings.BASE_DIR, 'data', 'rawdata_shortest.csv')
    # CSV 파일 읽기
    df = pd.read_csv(csv_file_path)
    # print(df)
    # 그래프 생성
    G = nx.Graph()

    # 각 줄에 있는 연결 정보를 읽어들여 그래프에 추가
    for _, row in df.iterrows():
        G.add_edge(row['Station A'], row['Station B'], weight=row['Weight'])

    return G

# 두 지점 간의 거리를 계산하는 함수 (Haversine 공식을 사용)
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # 지구 반경 (킬로미터)
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c * 1000  # 거리 (미터)

# 좌표로부터 가장 가까운 역을 찾는 함수
def calculate_nearest_station(lat, lng, stations):
    nearest_station = None
    min_distance = float('inf')
    for station in stations:
        distance = calculate_distance(lat, lng, station['latitude'], station['longitude'])
        if distance < min_distance:
            min_distance = distance
            nearest_station = station
    return nearest_station, min_distance

@csrf_exempt
def find_nearest_stations(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        start_lat = data.get('startLat')
        start_lng = data.get('startLng')
        end_lat = data.get('endLat')
        end_lng = data.get('endLng')

        # CSV 파일에서 역 데이터를 불러옴
        stations = load_stations_from_csv()

        # 출발지와 도착지 근처 가장 가까운 역 찾기
        nearest_start, start_distance = calculate_nearest_station(start_lat, start_lng, stations)
        nearest_end, end_distance = calculate_nearest_station(end_lat, end_lng, stations)

        return JsonResponse({
            'start_station': {
                'name': nearest_start['name'],
                'line': nearest_start['line'],
                'distance': start_distance
            },
            'end_station': {
                'name': nearest_end['name'],
                'line': nearest_end['line'],
                'distance': end_distance
            }
        })
    return JsonResponse({'error': 'Invalid request method'}, status=405)

# 최단 경로를 계산하고 응답하는 함수
@csrf_exempt
def find_shortest_route(request):
    if request.method == 'POST':
        try:
            # JSON 데이터 읽기
            data = json.loads(request.body)
            start_station = data.get('startStation')
            end_station = data.get('endStation')

            if not start_station or not end_station:
                return JsonResponse({'error': '출발역과 도착역이 필요합니다.'}, status=400)

            # CSV에서 그래프 생성
            subway_graph = build_graph_from_csv()

            # 시작역과 도착역이 그래프에 존재하는지 확인
            if not subway_graph.has_node(start_station):
                return JsonResponse({'error': f'출발 역 "{start_station}"을(를) 찾을 수 없습니다.'}, status=404)

            if not subway_graph.has_node(end_station):
                return JsonResponse({'error': f'도착 역 "{end_station}"을(를) 찾을 수 없습니다.'}, status=404)

            # 최단 경로 계산 (Dijkstra 알고리즘)
            try:
                path = nx.dijkstra_path(subway_graph, start_station, end_station, weight='weight')
                path_length = nx.dijkstra_path_length(subway_graph, start_station, end_station, weight='weight')

                # 경로와 거리 정보를 JSON으로 반환
                route = [{'name': station} for station in path]
                return JsonResponse({'route': route, 'distance': path_length})

            except nx.NetworkXNoPath:
                return JsonResponse({'error': '경로를 찾을 수 없습니다.'}, status=404)

        except json.JSONDecodeError:
            return JsonResponse({'error': '잘못된 요청입니다.'}, status=400)
        except Exception as e:
            return JsonResponse({'error': f'서버 오류: {str(e)}'}, status=500)  # 기타 예외 처리

    return JsonResponse({'error': 'Invalid request method'}, status=405)


