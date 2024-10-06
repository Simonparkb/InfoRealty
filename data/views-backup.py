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
from django.http import JsonResponse
from math import radians, cos, sin, sqrt, atan2

# 전역 변수로 캐시할 데이터
stations_cache = None
graph_cache = None


def index(request):
    return render(request, 'index.html')


def log_activity(user, action):
    ActivityLog.objects.create(user=user, action=action)



def kakaomap(request):
    return render(request, 'kakao.html', {'stations': load_stations_from_csv()})

# Helper functions to load stations and build the graph
def load_stations_from_csv():
    global stations_cache
    if stations_cache is None:
        csv_file_path = os.path.join(settings.BASE_DIR, 'data', 'new_rawdata.csv')
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
                    # 환승 정보는 CSV에서 읽지 않고 나중에 계산됨
                }
                station_map[row['name']].append(station_info)

        for station_name, station_list in station_map.items():
            # 동일한 역 이름이 여러 노선에 걸쳐 있을 경우 환승역으로 처리
            is_transfer = len(station_list) > 1
            for station in station_list:
                station['transfer'] = is_transfer  # 환승 여부를 계산
            stations.extend(station_list)

        # 캐시에 저장
        stations_cache = stations

    return stations_cache

def create_optimized_graph():
    global graph_cache
    if graph_cache is None:
        csv_file_path = os.path.join(settings.BASE_DIR, 'data', 'new_rawdata.csv')

        # CSV 파일 읽기
        try:
            df = pd.read_csv(csv_file_path)
            print("CSV 파일 읽기 성공")
        except Exception as e:
            print(f"CSV 파일을 읽는 중 오류가 발생했습니다: {e}")
            return None

        # 무방향 그래프 생성
        G = nx.Graph()

        try:
            # 1. 같은 노선에서 인접한 역들 간의 연결 (가중치 1)
            for line, line_data in df.groupby('line'):
                line_data = line_data.reset_index(drop=True)

                for i in range(len(line_data) - 1):
                    # 역과 노선을 함께 연결
                    G.add_edge(f"{line_data.loc[i, 'name']} ({line}호선)",
                               f"{line_data.loc[i + 1, 'name']} ({line}호선)", weight=1)
                print(f"{line} 노선 연결 완료")

            # 2. 같은 이름을 가진 다른 노선 간의 연결 (환승, 가중치 2)
            for station_name, matching_stations in df.groupby('name'):
                if len(matching_stations) > 1:
                    for i, row in matching_stations.iterrows():
                        for j, row2 in matching_stations.iterrows():
                            if i < j:
                                # 같은 이름의 다른 노선 간 연결
                                G.add_edge(f"{row['name']} ({row['line']}호선)",
                                           f"{row2['name']} ({row2['line']}호선)",
                                           weight=2)
            print("환승 연결 완료")

            graph_cache = G
            print("그래프 생성 완료")

        except Exception as e:
            print(f"그래프 생성 중 오류가 발생했습니다: {e}")
            return None

    return graph_cache
@csrf_exempt
def find_shortest_route(request):
    if request.method == 'POST':
        try:
            # JSON 데이터 읽기
            data = json.loads(request.body)
            start_station = data.get('startStation')
            end_station = data.get('endStation')
            print(data)
            if not start_station or not end_station:
                return JsonResponse({'error': '출발역과 도착역이 필요합니다.'}, status=400)

            # CSV에서 그래프 생성
            subway_graph = create_optimized_graph()

            # 출발역과 도착역을 정확히 매칭 (노선 정보 포함)
            start_station_with_line = next((n for n in subway_graph.nodes if start_station in n), None)
            end_station_with_line = next((n for n in subway_graph.nodes if end_station in n), None)

            if not start_station_with_line:
                return JsonResponse({'error': f'출발 역 "{start_station}"을(를) 찾을 수 없습니다.'}, status=404)

            if not end_station_with_line:
                return JsonResponse({'error': f'도착 역 "{end_station}"을(를) 찾을 수 없습니다.'}, status=404)

            # 최단 경로 계산 (Dijkstra 알고리즘 사용)
            try:
                path = nx.dijkstra_path(subway_graph, start_station_with_line, end_station_with_line, weight='weight')

                # 환승역과 일반역 계산
                stations = load_stations_from_csv()  # 모든 역 데이터를 로드
                transfer_count = 0
                regular_count = 0

                route = []
                for i, station in enumerate(path):
                    # 역 이름과 노선을 기반으로 데이터를 찾음
                    station_info = next((s for s in stations if station == f"{s['name']} ({s['line']}호선)"), None)

                    if station_info:
                        print(i, station,station_info)
                        route.append({
                            'name': station_info['name'],
                            'line': station_info['line'],
                            'transfer': station_info['transfer']  # 환승 여부 표시
                        })
                        if station_info['transfer']:
                            transfer_count += 1
                        else:
                            regular_count += 1
                    else:
                        return JsonResponse({'error': f'역 "{station}"에 대한 정보를 찾을 수 없습니다.'}, status=404)

                # 경로와 역 개수 정보를 JSON으로 반환
                return JsonResponse({
                    'route': route,
                    'transfer_count': transfer_count,
                    'regular_count': regular_count
                })

            except nx.NetworkXNoPath:
                return JsonResponse({'error': '경로를 찾을 수 없습니다.'}, status=404)

        except json.JSONDecodeError:
            return JsonResponse({'error': '잘못된 요청입니다.'}, status=400)
        except Exception as e:
            return JsonResponse({'error': f'서버 오류: {str(e)}'}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)





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