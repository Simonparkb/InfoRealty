from django.core.management.base import BaseCommand
from django.db.models import Count
from helloworld.models import Station

# class Command(BaseCommand):
#     help = "Update is_transfer field to True for stations with the same name on different lines"
#
#     def handle(self, *args, **kwargs):
#         # Step 1: 동일한 역 이름을 가진 경우의 수를 그룹화하여 확인
#         stations_to_update = (
#             Station.objects
#             .values('name')
#             .annotate(line_count=Count('line', distinct=True))
#             .filter(line_count__gt=1)
#         )
#
#         # Step 2: 환승역으로 확인된 역들만 업데이트
#         transfer_names = [station['name'] for station in stations_to_update]
#         updated_count = Station.objects.filter(name__in=transfer_names).update(is_transfer=True)
#
#         # Step 3: 결과 메시지 출력
#         self.stdout.write(self.style.SUCCESS(f"{updated_count} stations updated as transfer stations"))

from django.core.management.base import BaseCommand
from django.utils import timezone
from helloworld.models import Station  # 적절한 앱 이름으로 수정

class Command(BaseCommand):
    help = 'Fill opening_date with 1990-01-01 for records with null opening_date'

    def handle(self, *args, **kwargs):
        default_date = timezone.datetime(1990, 1, 1).date()
        stations = Station.objects.filter(opening_date__isnull=True)
        count = stations.update(opening_date=default_date)

        self.stdout.write(self.style.SUCCESS(f'Successfully updated opening_date for {count} stations.'))

# import csv
# import os
# from django.core.management.base import BaseCommand
# from django.conf import settings
# from helloworld.models import Station
#
#
# class Command(BaseCommand):
#     help = 'Import subway stations from CSV to the database'
#
#     def handle(self, *args, **kwargs):
#         # CSV 파일 경로 설정
#         csv_file_path = os.path.join(settings.BASE_DIR, 'data', 'new_rawdata.csv')
#
#         with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
#             reader = csv.reader(csvfile)
#             next(reader)  # 첫 번째 줄은 헤더이므로 건너뜁니다.
#
#             # CSV 파일에서 데이터 삽입
#             for row in reader:
#                 # 5개의 값을 읽음: line, name, latitude, longitude, sort_order
#                 line, name, latitude, longitude, sort_order = row
#                 Station.objects.create(
#                     line=line,
#                     name=name,
#                     latitude=float(latitude),
#                     longitude=float(longitude),
#                     sort_order=int(sort_order)  # sort_order는 정수형으로 변환
#                 )
#
#         self.stdout.write(self.style.SUCCESS('Successfully imported CSV data to database.'))