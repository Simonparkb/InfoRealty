import csv
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from helloworld.models import Station


class Command(BaseCommand):
    help = 'Import subway stations from CSV to the database'

    def handle(self, *args, **kwargs):
        # CSV 파일 경로 설정
        csv_file_path = os.path.join(settings.BASE_DIR, 'data', 'new_rawdata.csv')

        with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)  # 첫 번째 줄은 헤더이므로 건너뜁니다.

            # CSV 파일에서 데이터 삽입
            for row in reader:
                # 5개의 값을 읽음: line, name, latitude, longitude, sort_order
                line, name, latitude, longitude, sort_order = row
                Station.objects.create(
                    line=line,
                    name=name,
                    latitude=float(latitude),
                    longitude=float(longitude),
                    sort_order=int(sort_order)  # sort_order는 정수형으로 변환
                )

        self.stdout.write(self.style.SUCCESS('Successfully imported CSV data to database.'))