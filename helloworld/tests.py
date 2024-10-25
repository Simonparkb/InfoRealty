from django.test import TestCase

# Create your tests here.
import requests
import pandas as pd
import geopandas as gpd
# from .models import ActivityLog
import math
import csv
from collections import defaultdict
from django.shortcuts import render
import os
import json
import pandas as pd
import networkx as nx
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt


    # CSV 파일 경로 설정
    csv_file_path = os.path.join('C:\\Users\\parkk\\PycharmProjects\\infoRealty\\myDjango\\data\\rawdata.csv')

    # CSV 파일 읽기
    df = pd.read_csv(csv_file_path)

    # 무방향 그래프 생성
    G = nx.Graph()

    # 1. 같은 노선에서 인접한 역들 간의 연결 (가중치 1)
    for line, line_data in df.groupby('line'):
        line_data = line_data.reset_index(drop=True)

        # 연속된 역들 간의 연결 정보를 그래프에 추가
        G.add_edges_from([(line_data.loc[i, 'name'], line_data.loc[i + 1, 'name'], {'weight': 1})
                          for i in range(len(line_data) - 1)])

    # 2. 같은 이름을 가진 다른 노선 간의 연결 (환승, 가중치 2)
    df['station_prefix'] = df['name'].str.extract(r'^(.*)\(')
    for station_prefix, matching_stations in df.groupby('station_prefix'):
        if len(matching_stations) > 1:
            G.add_edges_from([(row['name'], row2['name'], {'weight': 2})
                              for i, row in matching_stations.iterrows()
                              for j, row2 in matching_stations.iterrows() if i < j])

    # 3. 환승역과 인접한 다른 노선의 역 간의 연결 (가중치 1)
    coord_group = df.groupby(['Latitude', 'Longitude'])
    for _, group in coord_group:
        if len(group) > 1:
            G.add_edges_from([(row['name'], row2['name'], {'weight': 1})
                              for i, row in group.iterrows()
                              for j, row2 in group.iterrows() if i < j])

    # 그래프를 데이터프레임으로 변환 (간선 정보 추출)
    shortest_paths = pd.DataFrame(nx.to_pandas_edgelist(G))

    # 결과 CSV로 저장
    output_csv_path = os.path.join('C:\\Users\\parkk\\PycharmProjects\\infoRealty\\myDjango\\rawdata_optimized.csv')
    shortest_paths.to_csv(output_csv_path, index=False)

    return output_csv_path

# 실행하여 CSV 파일 생성
output_csv_path = create_optimized_graph()
print(f"CSV 파일이 생성되었습니다: {output_csv_path}")
#
# API_KEY = "552201d8f67738ced76422ee252b3ac8"
#
#
# # 주소를 좌표로 변환
# def convert_address_to_coordinates(address):
#     api_url = "https://dapi.kakao.com/v2/local/search/address.json"
#     headers = {"Authorization": f"KakaoAK {API_KEY}"}
#
#     params = {"query": address}
#
#     try:
#         response = requests.get(api_url, headers=headers, params=params)
#         response.raise_for_status()
#         result = response.json()
#
#         if "documents" in result and len(result["documents"]) > 0:
#             coordinates = result["documents"][0]["y"], result["documents"][0]["x"]
#             return coordinates
#         else:
#             return None
#     except requests.exceptions.RequestException as e:
#         print(f"An error occurred: {e}")
#         return None
#
#
# # 데이터프레임에 좌표 추가
# def add_coordinates_to_dataframe(df, address_column):
#     latitudes = []
#     longitudes = []
#
#     for address in df[address_column]:
#         coordinates = convert_address_to_coordinates(address)
#         if coordinates:
#             latitudes.append(coordinates[0])
#             longitudes.append(coordinates[1])
#         else:
#             latitudes.append(None)
#             longitudes.append(None)
#
#     df["Latitude"] = latitudes
#     df["Longitude"] = longitudes
#
#
# # 데이터프레임
# # data = {'Name': ['서울역', '청담역', '삼셩역'],
# #         'Address': ['서울특별시 중구 남대문로5가 73-6 서울역(1호선)', '서울특별시 종로구 종로3가 10-5 종로3가역(1호선)', '서울특별시 마포구 신촌로 지하180(염리동)']}
# df = pd.read_csv('SeoulSubwayData1.csv')
# # df = pd.DataFrame(data)
#
# # 주소를 좌표로 변환하여 데이터프레임에 추가
# add_coordinates_to_dataframe(df, 'Address')
# df.to_csv('korea_np.csv', index=False, encoding='utf-8-sig')
# # df.head()
#
# <!DOCTYPE html>
# <html lang="ko">
# <head>
#     <meta charset="UTF-8">
#     <meta name="viewport" content="width=device-width, initial-scale=1.0">
#     <title>미래 도시 정보</title>
# </head>
# <body>
#     <h1></h1>
#     <ul>
#         <!-- 클릭 시 해당 위도, 경도를 파라미터로 전달 -->
#         <li><a href="infoRealty?lat=37.5796&lng=126.9027">2024</a></li>
#         <li><a href="infoRealty?lat=37.4784&lng=126.8646">2025</a></li>
#     </ul>
# </body>
# </html>

# views.py
# # Helper functions to load stations and build the graph
# def load_stations_from_csv():
#     global stations_cache
#     if stations_cache is None:
#         csv_file_path = os.path.join(settings.BASE_DIR, 'data', 'new_rawdata.csv')
#         stations = []
#         station_map = defaultdict(list)
#
#         with open(csv_file_path, newline='', encoding='utf-8-sig') as csvfile:
#             reader = csv.DictReader(csvfile)
#             for row in reader:
#                 station_info = {
#                     'name': row['name'],
#                     'line': row['line'],
#                     'latitude': float(row['Latitude']),
#                     'longitude': float(row['Longitude']),
#                     # 환승 정보는 CSV에서 읽지 않고 나중에 계산됨
#                 }
#                 station_map[row['name']].append(station_info)
#
#         for station_name, station_list in station_map.items():
#             # 동일한 역 이름이 여러 노선에 걸쳐 있을 경우 환승역으로 처리
#             is_transfer = len(station_list) > 1
#             for station in station_list:
#                 station['transfer'] = is_transfer  # 환승 여부를 계산
#             stations.extend(station_list)
#
#         # 캐시에 저장
#         stations_cache = stations
#         print(stations_cache)
#     return stations_cache

# def create_optimized_graph():
#     global graph_cache
#     if graph_cache is None:
#         csv_file_path = os.path.join(settings.BASE_DIR, 'data', 'new_rawdata.csv')
#
#         # CSV 파일 읽기
#         try:
#             df = pd.read_csv(csv_file_path)
#             # print("CSV 파일 읽기 성공")
#         except Exception as e:
#             print(f"CSV 파일을 읽는 중 오류가 발생했습니다: {e}")
#             return None
#
#         # 무방향 그래프 생성
#         G = nx.Graph()
#
#         try:
#             # 1. 같은 노선에서 인접한 역들 간의 연결 (가중치: 호선별 이동시간)
#             for line, line_data in df.groupby('line'):
#                 line_data = line_data.reset_index(drop=True)
#
#                 travel_time = line_travel_times.get(str(line), 2.0)  # 기본 이동시간 2분
#
#                 for i in range(len(line_data) - 1):
#                     # 역과 노선을 함께 연결
#                     G.add_edge(
#                         f"({line}){line_data.loc[i, 'name']}",
#                         f"({line}){line_data.loc[i + 1, 'name']}",
#                         weight=travel_time  # 호선별 이동 시간 적용
#                     )
#                 # print(f"{line}호선 연결 완료")
#
#             # 2. 같은 이름을 가진 다른 노선 간의 연결 (환승, 가중치: 환승 시간)
#             for station_name, matching_stations in df.groupby('name'):
#                 if len(matching_stations) > 1:
#                     for i, row in matching_stations.iterrows():
#                         for j, row2 in matching_stations.iterrows():
#                             if i < j:
#                                 # 같은 이름의 다른 노선 간 연결 (환승)
#                                 G.add_edge(
#                                     f"({row['line']}){row['name']}",
#                                     f"({row2['line']}){row2['name']}",
#                                     weight=transfer_time  # 환승 시간 적용
#                                 )
#             # print("환승 연결 완료")
#
#             graph_cache = G
#             # print("그래프 생성 완료")
#
#         except Exception as e:
#             print(f"그래프 생성 중 오류가 발생했습니다: {e}")
#             return None
#
#     return graph_cache
#

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
# Standard library imports
# import os
# import csv
# import json
# import math
# import logging
# from collections import defaultdict
# from math import radians, cos, sin, sqrt, atan2
#
# # Third-party imports
# import pandas as pd
# import networkx as nx
#
# # Django imports
# from django.conf import settings
# from django.db import transaction
# from django.db.models import F, Max  # F and Max for database field operations
# from django.shortcuts import render, get_object_or_404
# from django.views.decorators.csrf import csrf_exempt
# from django.http import JsonResponse
# from django.db.models.signals import post_save, post_delete
# from django.dispatch import receiver
#
#
#
# # Local app imports
# from .models import Station  # Importing only Station from .models
#
#
# logger = logging.getLogger(__name__)
#
# station_logger = logging.getLogger('station_activity')
#
#
# @receiver(post_save, sender=Station)
# def log_station_save(sender, instance, created, **kwargs):
#     if created:
#         station_logger.info(f"Station added: {instance.name} (Line: {instance.line}) by user: {instance.modified_by}")
#     else:
#         station_logger.info(f"Station updated: {instance.name} (Line: {instance.line}) by user: {instance.modified_by}")
#
# @receiver(post_delete, sender=Station)
# def log_station_delete(sender, instance, **kwargs):
#     station_logger.info(f"Station deleted: {instance.name} (Line: {instance.line}) by user: {instance.modified_by}")
#
# # 전역 변수로 캐시할 데이터
# stations_cache = None
# graph_cache = None
#
# # 호선별 이동 시간을 정의한 딕셔너리
# line_travel_times = {
#     '1': 2.0,  # 1호선: 2분
#     '2': 1.8,  # 2호선: 1.8분
#     '3': 2.2,  # 3호선: 2.2분
#     '4': 2.1,  # 4호선: 2.1분
#     '5': 2.3,  # 5호선: 2.3분
#     '6': 2.4,  # 6호선: 2.4분
#     '7': 2.5,  # 7호선: 2.5분
#     '8': 2.6,  # 8호선: 2.6분
#     '9': 2.7,  # 9호선: 2.7분
#     'Sinbundang': 1.5  # 신분당선: 1.5분
# }
# # 환승 시간을 정의
# transfer_time = 5.0  # 환승 시간 5분
#
#
# def departures(request):
#     return render(request, 'departures.html')
#
# def arrivals(request):
#     return render(request, 'arrivals.html')
#
# def services(request):
#     return render(request, 'services.html')
#
# def log_activity(user, action):
#     ActivityLog.objects.create(user=user, action=action)
#
#
# def kakaomap(request):
#     return render(request, 'kakao.html', {'stations': load_stations_from_csv()})
#
# def station_map(request):
#     stations = Station.objects.all()  # 모든 역 데이터 가져오기
#     return render(request, 'kakao.html', {
#         'stations': stations  # 템플릿에 역 정보 전달
#     })
#
# # Helper function to load stations from the database
# def load_stations_from_csv():
#     global stations_cache
#     if stations_cache is None:
#         stations = []
#         station_map = defaultdict(list)
#
#         # Retrieve all station records from the database
#         for station in Station.objects.all():
#             station_info = {
#                 'name': station.name,
#                 'line': station.line,
#                 'latitude': station.latitude,
#                 'longitude': station.longitude,
#                 # 환승 정보는 DB에서 읽지 않고 나중에 계산됨
#             }
#             station_map[station.name].append(station_info)
#
#         for station_name, station_list in station_map.items():
#             # 동일한 역 이름이 여러 노선에 걸쳐 있을 경우 환승역으로 처리
#             is_transfer = len(station_list) > 1
#             for station in station_list:
#                 station['transfer'] = is_transfer  # 환승 여부를 계산
#             stations.extend(station_list)
#         print(stations)
#         # Cache the results
#         stations_cache = stations
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
#
#         except Exception as e:
#             print(f"An error occurred while creating the graph: {e}")
#             return None
#
#     return graph_cache
#
#
#
# @csrf_exempt
# def find_shortest_route(request):
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             start_station = data.get('startStation')
#             end_station = data.get('endStation')
#             exclude_lines = data.get('exclude_lines', [])  # 제외할 노선을 받음. 없으면 빈 리스트
#             print(start_station, end_station, exclude_lines)
#
#             if not start_station or not end_station:
#                 return JsonResponse({'error': '출발역과 도착역이 필요합니다.'}, status=400)
#
#             # 최적화된 그래프 생성
#             subway_graph = create_optimized_graph()
#
#             # # 제외할 노선이 있는 경우 해당 노선의 역들을 그래프에서 제거
#             # if exclude_lines:
#             #     nodes_to_remove = [n for n in subway_graph.nodes if any(f"({line})" in n for line in exclude_lines)]
#             #     subway_graph.remove_nodes_from(nodes_to_remove)
#
#             # 출발역과 도착역을 정확히 매칭 (노선 정보 포함)
#             start_station_with_line = next((n for n in subway_graph.nodes if start_station in n), None)
#             end_station_with_line = next((n for n in subway_graph.nodes if end_station in n), None)
#             # print(start_station_with_line, end_station_with_line)
#
#             if not start_station_with_line:
#                 return JsonResponse({'error': f'출발 역 "{start_station}"을(를) 찾을 수 없습니다.'}, status=404)
#
#             if not end_station_with_line:
#                 return JsonResponse({'error': f'도착 역 "{end_station}"을(를) 찾을 수 없습니다.'}, status=404)
#
#             # 최단 경로 계산 (Dijkstra 알고리즘 사용)
#             try:
#                 path = nx.dijkstra_path(subway_graph, start_station_with_line, end_station_with_line, weight='weight')
#
#                 # CSV에서 역 정보 로드
#                 stations = load_stations_from_csv()
#                 total_time = 0  # 종합 시간 초기화
#                 transfer_count = 0
#                 regular_count = 0
#
#                 route = []
#                 for i in range(len(path) - 1):
#                     current_station = path[i]
#                     next_station = path[i + 1]
#
#                     # 현재 역과 다음 역 정보 가져오기
#                     current_station_info = next(
#                         (s for s in stations if current_station == f"({s['line']}){s['name']}"), None)
#                     next_station_info = next((s for s in stations if next_station == f"({s['line']}){s['name']}"), None)
#
#                     if current_station_info and next_station_info:
#                         route.append({
#                             'name': current_station_info['name'],
#                             'line': current_station_info['line'],
#                             'transfer': current_station_info['transfer']
#                         })
#
#                         if current_station_info['line'] == next_station_info['line']:
#                             # 같은 노선에 있는 경우, 호선별 이동 시간 계산
#                             travel_time = calculate_travel_time(current_station_info['line'])
#                         else:
#                             # 다른 노선으로 환승하는 경우, 환승 시간 추가
#                             travel_time = calculate_transfer_time()
#                             transfer_count += 1
#
#                         total_time += travel_time  # 이동 시간을 종합 시간에 더하기
#                         regular_count += 1 if not current_station_info['transfer'] else 0
#                     else:
#                         return JsonResponse({'error': f'역 "{current_station}" 또는 "{next_station}"에 대한 정보를 찾을 수 없습니다.'},
#                                             status=404)
#
#                 # 도착역 추가
#                 route.append({
#                     'name': next_station_info['name'],
#                     'line': next_station_info['line'],
#                     'transfer': next_station_info['transfer']
#                 })
#                 print(route)
#                 return JsonResponse({
#                     'route': route,
#                     'total_time': total_time,  # 종합 시간을 포함
#                     'transfer_count': transfer_count,
#                     'regular_count': regular_count
#                 })
#
#             except nx.NetworkXNoPath:
#                 return JsonResponse({'error': '경로를 찾을 수 없습니다.'}, status=404)
#
#         except json.JSONDecodeError:
#             return JsonResponse({'error': '잘못된 요청입니다.'}, status=400)
#         except Exception as e:
#             return JsonResponse({'error': f'서버 오류: {str(e)}'}, status=500)
#
#     return JsonResponse({'error': 'Invalid request method'}, status=405)
#
# # 호선별 이동 시간 계산
# def calculate_travel_time(line):
#     return line_travel_times.get(str(line), 2.0)  # 기본값은 2분
#
# # 환승 시간 계산
# def calculate_transfer_time():
#     return transfer_time  # 환승 시간은 고정 5분 (예시)
#
#
#
# # 두 지점 간의 거리를 계산하는 함수 (Haversine 공식을 사용)
# def calculate_distance(lat1, lon1, lat2, lon2):
#     try:
#         # 좌표 값이 문자열일 수 있으니 float으로 변환
#         lat1 = float(lat1)
#         lon1 = float(lon1)
#         lat2 = float(lat2)
#         lon2 = float(lon2)
#
#         R = 6371  # 지구 반경 (킬로미터)
#         dLat = math.radians(lat2 - lat1)
#         dLon = math.radians(lon2 - lon1)
#         a = math.sin(dLat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon / 2) ** 2
#         c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
#         distance = R * c * 1000  # 거리 계산 (미터 단위)
#         return distance
#     except ValueError as e:
#         print(f"ValueError calculating distance: {e}")
#         return float('inf')  # 오류 시 매우 큰 값 반환
#     except Exception as e:
#         print(f"Error calculating distance: {e}")
#         return float('inf')
#
# def find_nearest_stations_by_line(lat, lng, stations):
#     # 노선을 기준으로 그룹화
#     stations_by_line = {}
#     for station in stations:
#         line = station['line']
#         if line not in stations_by_line:
#             stations_by_line[line] = []
#         stations_by_line[line].append(station)
#
#     nearest_stations = {}
#
#     # 각 노선별로 가장 가까운 역 찾기
#     for line, stations in stations_by_line.items():
#         nearest_station = None
#         min_distance = float('inf')
#         for station in stations:
#             distance = calculate_distance(lat, lng, station['latitude'], station['longitude'])
#             if distance < min_distance:
#                 min_distance = distance
#                 nearest_station = station
#         # 결과를 출력 및 저장
#         if nearest_station:
#             nearest_stations[line] = {
#                 'station': nearest_station['name'],
#                 'distance': min_distance
#             }
#             # print(f"{line}호선: {nearest_station['name']} 역, 거리: {min_distance:.2f}m")
#
#     return nearest_stations
#
# @csrf_exempt
# def find_nearest_stations(request):
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             start_lat = data.get('startLat')
#             start_lng = data.get('startLng')
#             # include_lines = data.get('includeLines', [])
#             # print(include_lines)
#             if start_lat is None or start_lng is None:
#                 return JsonResponse({'error': '좌표 정보가 필요합니다.'}, status=400)
#
#             # 역 데이터 불러오기 (예: CSV 파일에서 불러오기)
#             stations = load_stations_from_csv()
#
#
#             # 선택된 노선 필터링
#             filtered_stations = [station for station in stations]
#             # filtered_stations = [station for station in stations if station['line'] in include_lines]
#             # print(start_lat, start_lng, "좌표와 필터링된 역 목록:")
#             # print(filtered_stations)
#
#             if not filtered_stations:
#                 return JsonResponse({'error': '선택된 노선에 해당하는 사용 가능한 역이 없습니다.'}, status=404)
#
#             # 노선별로 가장 가까운 역 찾기
#             nearest_stations = find_nearest_stations_by_line(start_lat, start_lng, filtered_stations)
#
#             # 상위 3개 역만 반환
#             top_3_stations = dict(sorted(nearest_stations.items(), key=lambda item: item[1]['distance'])[:3])
#             # 걷는 시간 계산 (100미터 당 70초)
#             walk_time_per_meter = 70 / 100
#             for line, station_info in top_3_stations.items():
#                 distance = station_info['distance']
#                 walk_time_minutes = (distance * walk_time_per_meter) / 60  # 분 단위로 변환
#                 station_info['walk_time'] = round(walk_time_minutes, 1)  # 소수점 1자리로 반올림
#
#             # print(top_3_stations)
#             return JsonResponse({
#                 'nearest_stations': top_3_stations
#             })
#         except Exception as e:
#             logger.error(f"Error in find_nearest_stations: {e}")
#             return JsonResponse({'error': '서버 오류가 발생했습니다.'}, status=500)
#
#     return JsonResponse({'error': 'Invalid request method'}, status=405)
#
# @csrf_exempt
# def add_station(request):
#
#     if request.method == 'POST':
#         station_logger.info(f"Station added: {station.name} (Line: {station.line}) by user: {request.user}")
#         try:
#             data = json.loads(request.body)
#
#             # 필수 필드 확인
#             required_fields = ['name', 'latitude', 'longitude', 'line']
#             if not all(field in data for field in required_fields):
#                 return JsonResponse({'status': 'error', 'message': 'Missing required fields'}, status=400)
#
#             # 중복 역 방지
#             if Station.objects.filter(name=data['name'], latitude=data['latitude'], longitude=data['longitude']).exists():
#                 return JsonResponse({'status': 'error', 'message': 'A station with the same name and location already exists.'}, status=400)
#
#             # 역 추가 위치 관련 변수
#             position = data.get('position')
#             selected_station_sort_order = data.get('selectedStationSortOrder')
#             sort_order = None
#
#             if position and selected_station_sort_order is not None:
#                 # `sort_order`를 선택한 역을 기준으로 설정
#                 if position == 'before':
#                     Station.objects.filter(line=data['line'], sort_order__gte=selected_station_sort_order).update(sort_order=F('sort_order') + 1)
#                     sort_order = selected_station_sort_order
#                 elif position == 'after':
#                     Station.objects.filter(line=data['line'], sort_order__gt=selected_station_sort_order).update(sort_order=F('sort_order') + 1)
#                     sort_order = selected_station_sort_order + 1
#             else:
#                 # 지정된 위치가 없을 경우, `sort_order`를 노선의 마지막 순서로 설정
#                 max_sort_order = Station.objects.filter(line=data['line']).aggregate(Max('sort_order'))['sort_order__max']
#                 sort_order = max_sort_order + 1 if max_sort_order is not None else 1
#
#             # 새 역 생성 및 저장
#             new_station = Station(
#                 name=data['name'],
#                 line=data['line'],
#                 latitude=data['latitude'],
#                 longitude=data['longitude'],
#                 sort_order=sort_order
#             )
#             new_station.save()
#
#             return JsonResponse({'status': 'success', 'message': 'Station added successfully'}, status=201)
#
#         except json.JSONDecodeError:
#             return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
#     else:
#         return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)
#
# @csrf_exempt
# def delete_station(request, station_name, station_line):
#     if request.method == 'DELETE':
#         station_logger.info(f"Station deleted: {station.name} (Line: {station.line}) by user: {request.user}")
#         try:
#             # 삭제할 역을 `name`과 `line`으로 필터링, 정확한 하나의 역만 삭제
#             station_to_delete = Station.objects.filter(name=station_name, line=station_line).first()
#             if not station_to_delete:
#                 return JsonResponse({'status': 'error', 'message': 'Station not found'}, status=404)
#
#             # 삭제할 역의 `sort_order`를 가져온 후 삭제
#             sort_order_to_delete = station_to_delete.sort_order
#             station_to_delete.delete()
#
#             # 삭제한 역 이후의 역들의 `sort_order`를 재조정
#             Station.objects.filter(line=station_line, sort_order__gt=sort_order_to_delete).update(sort_order=F('sort_order') - 1)
#
#             return JsonResponse({'status': 'success', 'message': 'Station deleted successfully'}, status=200)
#
#         except Station.DoesNotExist:
#             return JsonResponse({'status': 'error', 'message': 'Station not found'}, status=404)
#
#     return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)
#
#
# def station_detail(request, station_name, station_line):
#     print(f"요청된 역 이름: {station_name}, 요청된 노선: {station_line}")  # 디버깅용 출력
#
#     # DB에서 역 이름과 노선 번호로 검색
#     station = Station.objects.filter(name__iexact=station_name, line__iexact=station_line).first()
#
#     if not station:
#         return JsonResponse({'error': '역을 찾을 수 없습니다.'}, status=404)
#
#     station_data = {
#         'name': station.name,
#         'line': station.line,
#         'latitude': station.latitude,
#         'longitude': station.longitude,
#         'sort_order': station.sort_order
#     }
#
#     print(f"찾은 역 정보: {station_data}")  # 디버깅용 출력
#     return JsonResponse(station_data)
#
#
# def get_line_images(request):
#     images_dir = os.path.join(settings.STATICFILES_DIRS[0], 'image')
#     images = []
#
#     if os.path.exists(images_dir):
#         for image_file in os.listdir(images_dir):
#             if image_file.endswith('.png'):  # PNG 파일만 필터링
#                 images.append({
#                     'name': image_file,
#                     'url': f'/static/image/{image_file}'
#                 })
#
#     return JsonResponse({'images': images})
#
# # Define your view to load and display the CSV data
# def display_csv(request):
#     csv_file_path = os.path.join(settings.BASE_DIR, 'data', 'new_rawdata.csv')
#     stations = []
#
#     # Read the CSV file
#     with open(csv_file_path, newline='', encoding='utf-8-sig') as csvfile:
#         reader = csv.DictReader(csvfile)
#         for row in reader:
#             stations.append(row)
#
#     # Pass the CSV data to the template
#     return render(request, 'display_csv.html', {'stations': stations})