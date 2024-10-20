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
import logging
from django.http import JsonResponse

logger = logging.getLogger(__name__)

# 전역 변수로 캐시할 데이터
stations_cache = None
graph_cache = None

# 호선별 이동 시간을 정의한 딕셔너리
line_travel_times = {
    '1': 2.0,  # 1호선: 2분
    '2': 1.8,  # 2호선: 1.8분
    '3': 2.2,  # 3호선: 2.2분
    '4': 2.1,  # 4호선: 2.1분
    '5': 2.3,  # 5호선: 2.3분
    '6': 2.4,  # 6호선: 2.4분
    '7': 2.5,  # 7호선: 2.5분
    '8': 2.6,  # 8호선: 2.6분
    '9': 2.7,  # 9호선: 2.7분
    'Sinbundang': 1.5  # 신분당선: 1.5분
}
# 환승 시간을 정의
transfer_time = 5.0  # 환승 시간 5분

def departures(request):
    return render(request, 'departures.html')


def arrivals(request):
    return render(request, 'arrivals.html')

def services(request):
    return render(request, 'services.html')

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
            # print("CSV 파일 읽기 성공")
        except Exception as e:
            print(f"CSV 파일을 읽는 중 오류가 발생했습니다: {e}")
            return None

        # 무방향 그래프 생성
        G = nx.Graph()

        try:
            # 1. 같은 노선에서 인접한 역들 간의 연결 (가중치: 호선별 이동시간)
            for line, line_data in df.groupby('line'):
                line_data = line_data.reset_index(drop=True)

                travel_time = line_travel_times.get(str(line), 2.0)  # 기본 이동시간 2분

                for i in range(len(line_data) - 1):
                    # 역과 노선을 함께 연결
                    G.add_edge(
                        f"({line}){line_data.loc[i, 'name']}",
                        f"({line}){line_data.loc[i + 1, 'name']}",
                        weight=travel_time  # 호선별 이동 시간 적용
                    )
                # print(f"{line}호선 연결 완료")

            # 2. 같은 이름을 가진 다른 노선 간의 연결 (환승, 가중치: 환승 시간)
            for station_name, matching_stations in df.groupby('name'):
                if len(matching_stations) > 1:
                    for i, row in matching_stations.iterrows():
                        for j, row2 in matching_stations.iterrows():
                            if i < j:
                                # 같은 이름의 다른 노선 간 연결 (환승)
                                G.add_edge(
                                    f"({row['line']}){row['name']}",
                                    f"({row2['line']}){row2['name']}",
                                    weight=transfer_time  # 환승 시간 적용
                                )
            # print("환승 연결 완료")

            graph_cache = G
            # print("그래프 생성 완료")

        except Exception as e:
            print(f"그래프 생성 중 오류가 발생했습니다: {e}")
            return None

    return graph_cache







@csrf_exempt
def find_shortest_route(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            start_station = data.get('startStation')
            end_station = data.get('endStation')
            exclude_lines = data.get('exclude_lines', [])  # 제외할 노선을 받음. 없으면 빈 리스트
            print(start_station, end_station, exclude_lines)

            if not start_station or not end_station:
                return JsonResponse({'error': '출발역과 도착역이 필요합니다.'}, status=400)

            # 최적화된 그래프 생성
            subway_graph = create_optimized_graph()

            # # 제외할 노선이 있는 경우 해당 노선의 역들을 그래프에서 제거
            # if exclude_lines:
            #     nodes_to_remove = [n for n in subway_graph.nodes if any(f"({line})" in n for line in exclude_lines)]
            #     subway_graph.remove_nodes_from(nodes_to_remove)

            # 출발역과 도착역을 정확히 매칭 (노선 정보 포함)
            start_station_with_line = next((n for n in subway_graph.nodes if start_station in n), None)
            end_station_with_line = next((n for n in subway_graph.nodes if end_station in n), None)
            # print(start_station_with_line, end_station_with_line)

            if not start_station_with_line:
                return JsonResponse({'error': f'출발 역 "{start_station}"을(를) 찾을 수 없습니다.'}, status=404)

            if not end_station_with_line:
                return JsonResponse({'error': f'도착 역 "{end_station}"을(를) 찾을 수 없습니다.'}, status=404)

            # 최단 경로 계산 (Dijkstra 알고리즘 사용)
            try:
                path = nx.dijkstra_path(subway_graph, start_station_with_line, end_station_with_line, weight='weight')

                # CSV에서 역 정보 로드
                stations = load_stations_from_csv()
                total_time = 0  # 종합 시간 초기화
                transfer_count = 0
                regular_count = 0

                route = []
                for i in range(len(path) - 1):
                    current_station = path[i]
                    next_station = path[i + 1]

                    # 현재 역과 다음 역 정보 가져오기
                    current_station_info = next(
                        (s for s in stations if current_station == f"({s['line']}){s['name']}"), None)
                    next_station_info = next((s for s in stations if next_station == f"({s['line']}){s['name']}"), None)

                    if current_station_info and next_station_info:
                        route.append({
                            'name': current_station_info['name'],
                            'line': current_station_info['line'],
                            'transfer': current_station_info['transfer']
                        })

                        if current_station_info['line'] == next_station_info['line']:
                            # 같은 노선에 있는 경우, 호선별 이동 시간 계산
                            travel_time = calculate_travel_time(current_station_info['line'])
                        else:
                            # 다른 노선으로 환승하는 경우, 환승 시간 추가
                            travel_time = calculate_transfer_time()
                            transfer_count += 1

                        total_time += travel_time  # 이동 시간을 종합 시간에 더하기
                        regular_count += 1 if not current_station_info['transfer'] else 0
                    else:
                        return JsonResponse({'error': f'역 "{current_station}" 또는 "{next_station}"에 대한 정보를 찾을 수 없습니다.'},
                                            status=404)

                # 도착역 추가
                route.append({
                    'name': next_station_info['name'],
                    'line': next_station_info['line'],
                    'transfer': next_station_info['transfer']
                })
                print(route)
                return JsonResponse({
                    'route': route,
                    'total_time': total_time,  # 종합 시간을 포함
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

# 호선별 이동 시간 계산
def calculate_travel_time(line):
    return line_travel_times.get(str(line), 2.0)  # 기본값은 2분

# 환승 시간 계산
def calculate_transfer_time():
    return transfer_time  # 환승 시간은 고정 5분 (예시)







# 두 지점 간의 거리를 계산하는 함수 (Haversine 공식을 사용)
def calculate_distance(lat1, lon1, lat2, lon2):
    try:
        # 좌표 값이 문자열일 수 있으니 float으로 변환
        lat1 = float(lat1)
        lon1 = float(lon1)
        lat2 = float(lat2)
        lon2 = float(lon2)

        R = 6371  # 지구 반경 (킬로미터)
        dLat = math.radians(lat2 - lat1)
        dLon = math.radians(lon2 - lon1)
        a = math.sin(dLat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c * 1000  # 거리 계산 (미터 단위)
        return distance
    except ValueError as e:
        print(f"ValueError calculating distance: {e}")
        return float('inf')  # 오류 시 매우 큰 값 반환
    except Exception as e:
        print(f"Error calculating distance: {e}")
        return float('inf')

def find_nearest_stations_by_line(lat, lng, stations):
    # 노선을 기준으로 그룹화
    stations_by_line = {}
    for station in stations:
        line = station['line']
        if line not in stations_by_line:
            stations_by_line[line] = []
        stations_by_line[line].append(station)

    nearest_stations = {}

    # 각 노선별로 가장 가까운 역 찾기
    for line, stations in stations_by_line.items():
        nearest_station = None
        min_distance = float('inf')
        for station in stations:
            distance = calculate_distance(lat, lng, station['latitude'], station['longitude'])
            if distance < min_distance:
                min_distance = distance
                nearest_station = station
        # 결과를 출력 및 저장
        if nearest_station:
            nearest_stations[line] = {
                'station': nearest_station['name'],
                'distance': min_distance
            }
            # print(f"{line}호선: {nearest_station['name']} 역, 거리: {min_distance:.2f}m")

    return nearest_stations

@csrf_exempt
def find_nearest_stations(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            start_lat = data.get('startLat')
            start_lng = data.get('startLng')
            # include_lines = data.get('includeLines', [])
            # print(include_lines)
            if start_lat is None or start_lng is None:
                return JsonResponse({'error': '좌표 정보가 필요합니다.'}, status=400)

            # 역 데이터 불러오기 (예: CSV 파일에서 불러오기)
            stations = load_stations_from_csv()


            # 선택된 노선 필터링
            filtered_stations = [station for station in stations]
            # filtered_stations = [station for station in stations if station['line'] in include_lines]
            # print(start_lat, start_lng, "좌표와 필터링된 역 목록:")
            # print(filtered_stations)

            if not filtered_stations:
                return JsonResponse({'error': '선택된 노선에 해당하는 사용 가능한 역이 없습니다.'}, status=404)

            # 노선별로 가장 가까운 역 찾기
            nearest_stations = find_nearest_stations_by_line(start_lat, start_lng, filtered_stations)

            # 상위 3개 역만 반환
            top_3_stations = dict(sorted(nearest_stations.items(), key=lambda item: item[1]['distance'])[:3])
            # 걷는 시간 계산 (100미터 당 70초)
            walk_time_per_meter = 70 / 100
            for line, station_info in top_3_stations.items():
                distance = station_info['distance']
                walk_time_minutes = (distance * walk_time_per_meter) / 60  # 분 단위로 변환
                station_info['walk_time'] = round(walk_time_minutes, 1)  # 소수점 1자리로 반올림

            # print(top_3_stations)
            return JsonResponse({
                'nearest_stations': top_3_stations
            })
        except Exception as e:
            logger.error(f"Error in find_nearest_stations: {e}")
            return JsonResponse({'error': '서버 오류가 발생했습니다.'}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)
#
# # 좌표로부터 가장 가까운 역을 찾는 함수
# def calculate_nearest_station(lat, lng, stations):
#     nearest_station = None
#     min_distance = float('inf')
#     for station in stations:
#         distance = calculate_distance(lat, lng, station['latitude'], station['longitude'])
#         if distance < min_distance:
#             min_distance = distance
#             nearest_station = station
#     return nearest_station, min_distance
