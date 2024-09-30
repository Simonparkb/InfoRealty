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