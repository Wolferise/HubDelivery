from django.shortcuts import render
import requests
import ast
import json
from .models import BPLA, HUB, ORDER
import math


def manage_drones():
    # Поочередно обрабатывает обновления всех дронов и отправляет обновленную информацию на бэкенд. По прилету дрона
    # требуется отправить хабу отправки и хабу прилета оповещения об окончании полета (IP хабов нужно будет взять
    # из локальной БД)

    # Для каждого активного дрона в локальной БД
    drones = BPLA.objects.all()
    for drone in drones:

        # Приближенно вычисляем новые широту и долготу при условии, что обновления идут 2 раза в минуту
        dep_hub = HUB.objects.filter(id=drone.cur_departure)
        dest_hub = HUB.objects.filter(id=drone.cur_destination)
        update_frequency_per_hour = 120
        new_lat = drone.latitude + (drone.speed / update_frequency_per_hour) * math.cos(drone.azimuth * math.pi / 180) / (6371000 * math.pi / 180)
        new_long = drone.longitude + (drone.speed / update_frequency_per_hour) * math.sin(drone.azimuth * math.pi / 180) / math.cos(drone.latitude * math.pi / 180) / (6371000 * math.pi / 180)
        print(new_lat, new_long)
        # Проверяем, что дрон не "перелетел" хаб доставки

        # Сохраняем новые данные о дроне
        drone.latitude = new_lat
        drone.longitude = new_long
        drone.save()

        # Отсылаем данные об обновлении дрона в БД бэкенда
        backend_add_drone_url = "http://backend_IP/api/drones"
        drone_dict = {'board_number': drone.id,
                      'type': drone.type,
                      'capacity': drone.capacity,
                      'speed': drone.speed,
                      'latitude': drone.latitude,
                      'longitude': drone.longitude,
                      'azimuth': drone.azimuth}
        drone_data = json.dumps(drone_dict)
        json.loads(requests.post(backend_add_drone_url, json=drone_data))


while True:
    manage_drones()

