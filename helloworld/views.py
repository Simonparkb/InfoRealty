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

def index(request):
    return render(request, 'index.html')

def log_activity(user, action):
    ActivityLog.objects.create(user=user, action=action)

def kakaomap(request):
    # CSV 파일 경로 설정
    # csv_file_path = os.path.join(settings.BASE_DIR,
    #                              'C:\\Users\\parkk\\PycharmProjects\\infoRealty\\myDjango\\data',
    #                              'rawdata.csv')
    csv_file_path = os.path.join(settings.BASE_DIR, 'data', 'rawdata.csv')

    # CSV 파일 읽기
    stations = []
    station_map = defaultdict(list)  # 역 이름을 키로 하고 각 역의 정보를 리스트로 저장

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

    # 중복된 역 이름을 처리하고 환승역으로 표시
    for station_name, station_list in station_map.items():
        lines = set([station['line'] for station in station_list])
        if len(lines) > 1:
            for station in station_list:
                station['transfer'] = True  # 환승역 처리
        stations.extend(station_list)

    # 템플릿에 역 데이터 전달
    return render(request, 'kakao.html', {'stations': stations})


# 두 지점 간의 거리를 계산하는 함수 (Haversine 공식을 사용)
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # 지구 반경 (킬로미터)
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c * 1000  # 거리 (미터)


# Helper functions to load stations and build the graph
def load_stations_from_csv(csv_file_path):
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

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # 지구 반경 (킬로미터)
    dLat = radians(lat2 - lat1)
    dLon = radians(lon2 - lon1)
    a = sin(dLat / 2) * sin(dLat / 2) + cos(radians(lat1)) * cos(radians(lat2)) * sin(dLon / 2) * sin(dLon / 2)
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c * 1000  # 거리 (미터)


def find_nearest_station(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        start_lat = data['startLat']
        start_lng = data['startLng']
        end_lat = data['endLat']
        end_lng = data['endLng']

        nearest_start = None
        nearest_end = None
        min_distance_start = float('inf')
        min_distance_end = float('inf')

        # 지하철역 정보를 데이터베이스에서 가져온다고 가정
        stations = Station.objects.all()

        for station in stations:
            start_distance = calculate_distance(start_lat, start_lng, station.latitude, station.longitude)
            end_distance = calculate_distance(end_lat, end_lng, station.latitude, station.longitude)

            if start_distance < min_distance_start:
                min_distance_start = start_distance
                nearest_start = station

            if end_distance < min_distance_end:
                min_distance_end = end_distance
                nearest_end = station

        return JsonResponse({
            'start_station': {
                'name': nearest_start.name,
                'line': nearest_start.line,
                'distance': min_distance_start
            },
            'end_station': {
                'name': nearest_end.name,
                'line': nearest_end.line,
                'distance': min_distance_end
            }
        })


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


