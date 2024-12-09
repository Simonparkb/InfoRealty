# Standard library imports
import os
import csv
import json
import math
import logging
from collections import defaultdict
from math import radians, cos, sin, sqrt, atan2

# Third-party imports
import pandas as pd
import networkx as nx

# Django imports
from django.conf import settings
from django.db import transaction
from django.db.models import F, Max  # F and Max for database field operations
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from collections import defaultdict
from .models import Station

# Local app imports
from .models import Station  # Importing only Station from .models

logger = logging.getLogger(__name__)

def log_activity(user, action):
    ActivityLog.objects.create(user=user, action=action)


def under_construction(request):
    return render(request, 'underconstruction.html')

def departures(request):
    return render(request, 'departures.html')

def arrivals(request):
    return render(request, 'arrivals.html')

def services(request):
    return render(request, 'services.html')

def station_map(request):
    # stations = Station.objects.all()  # 모든 역 데이터 가져오기
    return render(request, 'kakao.html', {'stations': load_stations_from_db()})





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
    '7': 0.5,  # 7호선: 2.5분
    '8': 2.6,  # 8호선: 2.6분
    '9': 2.7,  # 9호선: 2.7분
    'Sinbundang': 1.5,  # 신분당선: 1.5분
    'Suinbundang': 1.5  # 신분당선: 1.5분
}





def load_stations_from_db():
    global stations_cache
    if stations_cache is None:
        stations = []
        station_map = defaultdict(list)
        transfer_map = defaultdict(list)

        for station in Station.objects.all():
            station_info = {
                'name': station.name,
                'line': station.line,
                'latitude': int(station.latitude * 10000) / 10000,
                'longitude': int(station.longitude * 10000) / 10000,
                'sort_order': station.sort_order,
                'is_transfer': station.is_transfer,
                'is_branch_point': station.is_branch_point,
                'opening_date': station.opening_date,  # Add opening date
                'description': station.description,  # Add description
            }

            transfer_key = (station_info['name'], int(station.latitude), int(station.longitude))
            transfer_map[transfer_key].append(station_info)

            station_map[(station_info['name'], station_info['latitude'], station_info['longitude'])].append(station_info)

        for (station_name, latitude, longitude), station_list in station_map.items():
            transfer_key = (station_name, int(latitude), int(longitude))
            is_transfer = len(transfer_map[transfer_key]) > 1 or any(
                st['is_transfer'] for st in transfer_map[transfer_key]
            )

            for station in station_list:
                station['transfer'] = is_transfer
                station['branch_point'] = station['is_branch_point']

            stations.extend(station_list)

        # print("Loaded stations cache:", stations)
        stations_cache = stations
    return stations_cache

# 시간 설정
transfer_time = 5.0           # 다른 노선 간 환승 시간
default_travel_time = 2.0      # 같은 노선에서 기본 이동 시간

def create_optimized_graph():
    global graph_cache
    if graph_cache is None:
        G = nx.Graph()

        try:
            stations = Station.objects.all()
            stations_by_line = defaultdict(list)
            stations_by_name = defaultdict(list)

            for station in stations:
                stations_by_line[station.line].append(station)
                stations_by_name[station.name].append(station)

            # 1. 다른 노선 간 동일 역 이름을 가진 경우 환승 연결
            for station_name, matching_stations in stations_by_name.items():
                if len(matching_stations) > 1:
                    for i in range(len(matching_stations) - 1):
                        for j in range(i + 1, len(matching_stations)):
                            # 다른 노선 간 동일 역 이름을 가진 경우 환승 시간 적용
                            G.add_edge(
                                f"({matching_stations[i].line}){matching_stations[i].name}",
                                f"({matching_stations[j].line}){matching_stations[j].name}",
                                weight=transfer_time  # 다른 노선 간 환승 시간
                            )
                            print(f"Added transfer between lines at the same station: "
                                  f"{matching_stations[i].name} ({matching_stations[i].line}) ↔ "
                                  f"{matching_stations[j].name} ({matching_stations[j].line}) "
                                  f"with weight {transfer_time}")

            # 2. 같은 노선에서 sort_order 순서로 인접 연결
            for line, line_stations in stations_by_line.items():
                line_stations.sort(key=lambda x: x.sort_order)

                for i in range(len(line_stations) - 1):
                    current_station = line_stations[i]
                    next_station = line_stations[i + 1]

                    # 기본 가중치 설정
                    weight = default_travel_time

                    # is_transfer가 True인 경우 가중치를 줄여서 환승을 더 선호하도록 설정
                    if current_station.is_transfer or next_station.is_transfer:
                        weight *= 0.8  # 환승 가능한 역에 대한 가중치를 낮춰 더 선호하게 함
                        # print(f"Transfer available between {current_station.name} and {next_station.name} with weight {weight}")

                    # sort_order 차이가 작을수록 가중치를 줄여 인접성을 선호
                    sort_order_diff = abs(current_station.sort_order - next_station.sort_order)
                    weight -= sort_order_diff * 0.1  # 인접 역 우선

                    # 같은 노선 내 인접 역 연결
                    G.add_edge(
                        f"({line}){current_station.name}",
                        f"({line}){next_station.name}",
                        weight=weight
                    )
                    print(f"Connected adjacent stations on the same line: "
                          f"{current_station.name} ({current_station.line}) ↔ "
                          f"{next_station.name} ({next_station.line}) "
                          f"with weight {weight}")

            graph_cache = G
            print("Generated graph cache:", G.edges(data=True))
        except Exception as e:
            print(f"An error occurred while creating the graph: {e}")
            return None

    return graph_cache

@csrf_exempt
def find_shortest_route(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            start_station = data.get('startStation')
            end_station = data.get('endStation')
            exclude_lines = data.get('exclude_lines', [])  # List of lines to exclude, empty if not provided

            if not start_station or not end_station:
                return JsonResponse({'error': '출발역과 도착역이 필요합니다.'}, status=400)

            # Create optimized graph for pathfinding
            subway_graph = create_optimized_graph()

            # Remove nodes for excluded lines
            if exclude_lines:
                nodes_to_remove = [n for n in subway_graph.nodes if any(f"({line})" in n for line in exclude_lines)]
                subway_graph.remove_nodes_from(nodes_to_remove)

            # Match start and end stations with exact line info
            start_station_with_line = next((n for n in subway_graph.nodes if start_station in n), None)
            end_station_with_line = next((n for n in subway_graph.nodes if end_station in n), None)

            if not start_station_with_line:
                return JsonResponse({'error': f'출발 역 "{start_station}"을(를) 찾을 수 없습니다.'}, status=404)

            if not end_station_with_line:
                return JsonResponse({'error': f'도착 역 "{end_station}"을(를) 찾을 수 없습니다.'}, status=404)

            # Calculate the shortest path using Dijkstra's algorithm
            try:
                path = nx.dijkstra_path(subway_graph, start_station_with_line, end_station_with_line, weight='weight')
                stations = load_stations_from_db()
                total_time = 0  # Initialize total travel time
                transfer_count = 0
                regular_count = 0

                route = []
                for i in range(len(path) - 1):
                    current_station = path[i]
                    next_station = path[i + 1]

                    # Fetch station information for the current and next station
                    current_station_info = next(
                        (s for s in stations if current_station == f"({s['line']}){s['name']}"), None)
                    next_station_info = next(
                        (s for s in stations if next_station == f"({s['line']}){s['name']}"), None)

                    if current_station_info and next_station_info:
                        # Append current station details to the route
                        route.append({
                            'name': current_station_info['name'],
                            'line': current_station_info['line'],
                            'latitude': current_station_info['latitude'],
                            'longitude': current_station_info['longitude'],
                            'opening_date': current_station_info['opening_date'],
                            'description': current_station_info['description'],
                            'transfer': current_station_info['transfer']
                        })

                        # Calculate travel time and transfer count
                        if current_station_info['line'] == next_station_info['line']:
                            travel_time = calculate_travel_time(current_station_info['line'])
                        else:
                            travel_time = calculate_transfer_time()
                            transfer_count += 1

                        total_time += travel_time
                        regular_count += 1 if not current_station_info['transfer'] else 0
                    else:
                        return JsonResponse({'error': f'역 "{current_station}" 또는 "{next_station}"에 대한 정보를 찾을 수 없습니다.'},
                                            status=404)

                # Append the destination station details
                route.append({
                    'name': next_station_info['name'],
                    'line': next_station_info['line'],
                    'latitude': next_station_info['latitude'],
                    'longitude': next_station_info['longitude'],
                    'opening_date': next_station_info['opening_date'],
                    'description': next_station_info['description'],
                    'transfer': next_station_info['transfer']
                })

                # Return the route information with additional details
                return JsonResponse({
                    'route': route,
                    'total_time': total_time,
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
            stations = load_stations_from_db()


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

@csrf_exempt
def add_new_line(request):
    global stations_cache  # 전역 변수인 stations_cache를 사용합니다.
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name')
            line = data.get('line')
            latitude = data.get('latitude')
            longitude = data.get('longitude')

            # 동일한 line이 이미 존재하는지 확인
            if Station.objects.filter(line=line).exists():
                return JsonResponse({'message': '이미 존재하는 노선입니다. 다른 라인을 입력하세요.'}, status=400)

            # 신규 라인일 경우 sort_order를 1로 설정
            new_sort_order = 1

            # 새로운 역을 Station 모델에 추가
            new_station = Station.objects.create(
                name=name,
                line=line,
                latitude=latitude,
                longitude=longitude,
                sort_order=new_sort_order
            )
            # 캐시 초기화
            stations_cache = None
            return JsonResponse({'message': '신규 라인이 성공적으로 추가되었습니다.', 'station_id': new_station.id}, status=201)
        except Exception as e:
            return JsonResponse({'message': '신규 라인 추가 중 오류 발생: ' + str(e)}, status=400)
    return JsonResponse({'message': '허용되지 않은 메서드입니다.'}, status=405)

# @csrf_exempt
# def add_new_line(request):
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             name = data.get('name')
#             line = data.get('line')
#             latitude = data.get('latitude')
#             longitude = data.get('longitude')
#
#             # 동일한 line이 이미 존재하는지 확인
#             if Station.objects.filter(line=line).exists():
#                 return JsonResponse({'message': '이미 존재하는 노선입니다. 다른 라인을 입력하세요.'}, status=400)
#
#             # sort_order의 가장 높은 값에 1을 추가하여 새로운 순서 설정
#             max_sort_order = Station.objects.aggregate(Max('sort_order'))['sort_order__max'] or 0
#             new_sort_order = max_sort_order + 1
#
#             # 새로운 역을 Station 모델에 추가
#             new_station = Station.objects.create(
#                 name=name,
#                 line=line,
#                 latitude=latitude,
#                 longitude=longitude,
#                 sort_order=new_sort_order
#             )
#
#             return JsonResponse({'message': '신규 라인이 성공적으로 추가되었습니다.', 'station_id': new_station.id}, status=201)
#         except Exception as e:
#             return JsonResponse({'message': '신규 라인 추가 중 오류 발생: ' + str(e)}, status=400)
#     return JsonResponse({'message': '허용되지 않은 메서드입니다.'}, status=405)

@csrf_exempt
def add_station(request):
    global stations_cache  # 전역 변수인 stations_cache를 사용합니다.
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            # 필수 필드 확인
            required_fields = ['name', 'latitude', 'longitude', 'line']
            if not all(field in data for field in required_fields):
                return JsonResponse({'status': 'error', 'message': 'Missing required fields'}, status=400)

            # 중복 역 방지
            if Station.objects.filter(name=data['name'], latitude=data['latitude'], longitude=data['longitude']).exists():
                return JsonResponse({'status': 'error', 'message': 'A station with the same name and location already exists.'}, status=400)

            # 역 추가 위치 관련 변수
            position = data.get('position')
            selected_station_sort_order = data.get('selectedStationSortOrder')
            sort_order = None

            if position and selected_station_sort_order is not None:
                # 특정 위치부터 해당 노선 내 역들의 sort_order만 +1
                if position == 'before':
                    Station.objects.filter(line=data['line'], sort_order__gte=selected_station_sort_order).update(sort_order=F('sort_order') + 1)
                    sort_order = selected_station_sort_order
                elif position == 'after':
                    Station.objects.filter(line=data['line'], sort_order__gt=selected_station_sort_order).update(sort_order=F('sort_order') + 1)
                    sort_order = selected_station_sort_order + 1
            else:
                # 지정된 위치가 없을 경우, 해당 노선 내 마지막 sort_order + 1
                max_sort_order = Station.objects.filter(line=data['line']).aggregate(Max('sort_order'))['sort_order__max']
                sort_order = max_sort_order + 1 if max_sort_order is not None else 1

            # is_transfer 값이 제공되지 않으면 기본값 False로 설정
            is_transfer = data.get('is_transfer', False)

            # 새 역 생성 및 저장
            new_station = Station(
                name=data['name'],
                line=data['line'],
                latitude=data['latitude'],
                longitude=data['longitude'],
                sort_order=sort_order,
                is_transfer=is_transfer
            )
            new_station.save()

            # 캐시 초기화
            stations_cache = None

            return JsonResponse({'status': 'success', 'message': 'Station added successfully'}, status=201)

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)
@csrf_exempt
def delete_station(request, station_name, station_line):
    global stations_cache  # 전역 변수인 stations_cache를 사용합니다.
    if request.method == 'DELETE':
        try:
            # 삭제할 역을 `name`과 `line`으로 필터링하여 정확한 하나의 역만 삭제
            station_to_delete = Station.objects.filter(name=station_name, line=station_line).first()
            if not station_to_delete:
                return JsonResponse({'status': 'error', 'message': 'Station not found'}, status=404)

            # 삭제할 역의 sort_order를 가져온 후 삭제
            sort_order_to_delete = station_to_delete.sort_order
            station_to_delete.delete()

            # 삭제한 역의 위치 이후 해당 노선 내 역들의 sort_order만 -1
            Station.objects.filter(line=station_line, sort_order__gt=sort_order_to_delete).update(sort_order=F('sort_order') - 1)

            # 캐시 초기화
            stations_cache = None

            return JsonResponse({'status': 'success', 'message': 'Station deleted successfully'}, status=200)

        except Station.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Station not found'}, status=404)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

# @csrf_exempt
# def delete_station(request, station_name, station_line):
#     if request.method == 'DELETE':
#         try:
#             # 삭제할 역을 `name`과 `line`으로 필터링, 정확한 하나의 역만 삭제
#             station_to_delete = Station.objects.filter(name=station_name, line=station_line).first()
#             if not station_to_delete:
#                 return JsonResponse({'status': 'error', 'message': 'Station not found'}, status=404)
#
#             # 삭제할 역의 sort_order를 가져온 후 삭제
#             sort_order_to_delete = station_to_delete.sort_order
#             station_to_delete.delete()
#
#             # 삭제한 역의 위치 이후 역들의 sort_order만 -1
#             Station.objects.filter(sort_order__gt=sort_order_to_delete).update(sort_order=F('sort_order') - 1)
#
#             return JsonResponse({'status': 'success', 'message': 'Station deleted successfully'}, status=200)
#
#         except Station.DoesNotExist:
#             return JsonResponse({'status': 'error', 'message': 'Station not found'}, status=404)
#
#     return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)


@csrf_exempt
def update_station(request, station_name, station_line):
    global stations_cache  # 전역 변수인 stations_cache를 사용합니다.
    if request.method == 'PUT':
        try:
            # 요청 데이터에서 새로운 역 정보 가져오기
            data = json.loads(request.body)

            # 기존 역 정보 가져오기
            station = get_object_or_404(Station, name=station_name, line=station_line)

            # 역 정보 업데이트
            station.name = data.get('name', station.name)
            station.line = data.get('line', station.line)
            station.latitude = data.get('latitude', station.latitude)
            station.longitude = data.get('longitude', station.longitude)
            station.is_transfer = data.get('is_transfer', station.is_transfer)
            station.save()  # 변경사항 저장
            # 캐시 초기화
            stations_cache = None
            return JsonResponse({'status': 'success', 'message': 'Station updated successfully'}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

def station_detail(request, station_name, station_line):
    print(f"요청된 역 이름: {station_name}, 요청된 노선: {station_line}")  # 디버깅용 출력

    # DB에서 역 이름과 노선 번호로 검색
    station = Station.objects.filter(name__iexact=station_name, line__iexact=station_line).first()

    if not station:
        return JsonResponse({'error': '역을 찾을 수 없습니다.'}, status=404)

    station_data = {
        'name': station.name,
        'line': station.line,
        'latitude': station.latitude,
        'longitude': station.longitude,
        'sort_order': station.sort_order,
        'is_transfer': station.is_transfer  # is_transfer 필드 추가
    }

    print(f"찾은 역 정보: {station_data}")  # 디버깅용 출력
    return JsonResponse(station_data)


def get_line_images(request):
    images_dir = os.path.join(settings.STATICFILES_DIRS[0], 'image')
    images = []

    if os.path.exists(images_dir):
        for image_file in os.listdir(images_dir):
            if image_file.endswith('.png'):  # PNG 파일만 필터링
                images.append({
                    'name': image_file,
                    'url': f'/static/image/{image_file}'
                })

    return JsonResponse({'images': images})

# Define your view to load and display the CSV data
def display_csv(request):
    csv_file_path = os.path.join(settings.BASE_DIR, 'data', 'new_rawdata.csv')
    stations = []

    # Read the CSV file
    with open(csv_file_path, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            stations.append(row)

    # Pass the CSV data to the template
    return render(request, 'display_csv.html', {'stations': stations})




def kakaomap(request):
    return render(request, 'kakao.html', {'stations': load_stations_from_db()})

# def load_stations_from_db():
#     global stations_cache
#     if stations_cache is None:
#         stations = []
#         station_map = defaultdict(list)
#         transfer_map = defaultdict(list)
#
#         # Retrieve all station records from the database
#         for station in Station.objects.all():
#             # 소수점 넷째 자리에서 버림하여 위도와 경도 저장
#             station_info = {
#                 'name': station.name,
#                 'line': station.line,
#                 'latitude': int(station.latitude * 10000) / 10000,
#                 'longitude': int(station.longitude * 10000) / 10000,
#                 'sort_order': station.sort_order,
#                 'is_transfer': station.is_transfer,  # DB의 is_transfer 값을 사용
#             }
#             # (이름, 정수부 위도, 정수부 경도)를 키로 transfer_map에 추가 (환승 확인용)
#             transfer_key = (station_info['name'], int(station.latitude), int(station.longitude))
#             transfer_map[transfer_key].append(station_info)
#
#             # 소수점 이하 포함한 위치 정보를 기준으로 station_map에 추가 (캐시 저장용)
#             station_map[(station_info['name'], station_info['latitude'], station_info['longitude'])].append(
#                 station_info
#             )
#
#         # 환승 여부 설정
#         for (station_name, latitude, longitude), station_list in station_map.items():
#             # transfer_map을 참조하여 환승 여부 설정
#             transfer_key = (station_name, int(latitude), int(longitude))
#             is_transfer = len(transfer_map[transfer_key]) > 1 and all(
#                 st['is_transfer'] for st in transfer_map[transfer_key]
#             )
#
#             # station_map의 정보에 환승 여부를 반영
#             for station in station_list:
#                 station['transfer'] = is_transfer
#
#             stations.extend(station_list)
#
#         # Cache the results
#         stations_cache = stations
#         print(stations_cache)
#     return stations_cache
#
#
# # Function to create an optimized graph using data from the database
# def create_optimized_graph():
#     global graph_cache
#     if graph_cache is None:
#         # Initialize an undirected graph
#         G = nx.Graph()
#
#         try:
#             # Retrieve all station records from the database
#             stations = Station.objects.all()
#             # Dictionary to group stations by line and name
#             stations_by_line = defaultdict(list)
#             stations_by_name = defaultdict(list)
#
#             # Populate the stations_by_line and stations_by_name dictionaries
#             for station in stations:
#                 stations_by_line[station.line].append(station)
#                 stations_by_name[station.name].append(station)
#
#             # 1. Connect adjacent stations on the same line with weighted edges
#             for line, line_stations in stations_by_line.items():
#                 # Sort by 'sort_order' to ensure adjacency
#                 line_stations.sort(key=lambda x: x.sort_order)
#                 travel_time = line_travel_times.get(str(line), 2.0)  # Default travel time of 2 minutes
#
#                 for i in range(len(line_stations) - 1):
#                     # Connect consecutive stations on the same line
#                     G.add_edge(
#                         f"({line}){line_stations[i].name}",
#                         f"({line}){line_stations[i + 1].name}",
#                         weight=travel_time  # Apply travel time by line
#                     )
#
#             # 2. Connect stations with the same name on different lines (transfer stations)
#             for station_name, matching_stations in stations_by_name.items():
#                 if len(matching_stations) > 1:
#                     for i in range(len(matching_stations) - 1):
#                         for j in range(i + 1, len(matching_stations)):
#                             # Add an edge between stations on different lines with the same name
#                             G.add_edge(
#                                 f"({matching_stations[i].line}){matching_stations[i].name}",
#                                 f"({matching_stations[j].line}){matching_stations[j].name}",
#                                 weight=transfer_time  # Apply transfer time
#                             )
#
#             # Cache the generated graph
#             graph_cache = G
#         except Exception as e:
#             print(f"An error occurred while creating the graph: {e}")
#             return None
#
#     return graph_cache
#
#
#
