from django.shortcuts import render
import requests
import ast
import json
from .models import BPLA, HUB, ORDER
import math


def create_drone(request):
    if request.method == "POST":
        delivery_data = request.POST

        # Загружаем данные о хабе отправления и прибытия
        backend_url = "http://backend_IP/api/hubs"
        dep_hub_dict = {'hub_id': delivery_data['departure_hub_id']}
        dep_hub_dict = json.dumps(dep_hub_dict)
        dep_hub_data = json.loads(requests.get(backend_url, json=dep_hub_dict))
        dest_hub_dict = {'hub_id': delivery_data['destination_hub_id']}
        dest_hub_dict = json.dumps(dest_hub_dict)
        dest_hub_data = json.loads(requests.get(backend_url, json=dest_hub_dict))

        # Определяем тип дрона по формуле
        drone_type = min(dest_hub_data['type'], dep_hub_data['type']) + 1

        # Назначение скорости и грузоподьемности дрона в зависимости от типа
        # Добавить высчитывание азимута
        # pi - число pi, rad - радиус сферы (Земли)
        rad = 6372795

        # координаты двух точек
        llat1 = float(dep_hub_data['latitude'])
        llong1 = float(dep_hub_data['longitude'])

        llat2 = float(dest_hub_data['latitude'])
        llong2 = float(dest_hub_data['longitude'])

        # в радианах
        lat1 = llat1 * math.pi / 180.
        lat2 = llat2 * math.pi / 180.
        long1 = llong1 * math.pi / 180.
        long2 = llong2 * math.pi / 180.

        # косинусы и синусы широт и разницы долгот
        cl1 = math.cos(lat1)
        cl2 = math.cos(lat2)
        sl1 = math.sin(lat1)
        sl2 = math.sin(lat2)
        delta = long2 - long1
        cdelta = math.cos(delta)
        sdelta = math.sin(delta)

        # вычисление начального азимута
        x = (cl1 * sl2) - (sl1 * cl2 * cdelta)
        y = sdelta * cl2
        z = math.degrees(math.atan(-y / x))

        if x < 0:
            z = z + 180.

        z2 = (z + 180.) % 360. - 180.
        z2 = - math.radians(z2)
        anglerad2 = z2 - ((2 * math.pi) * math.floor((z2 / (2 * math.pi))))
        angledeg = (anglerad2 * 180.) / math.pi

        # Сохраняем дрон в локальную БД
        new_drone = BPLA(type=drone_type,
                         capacity=drone_type * 500, # костыли
                         speed= drone_type * 30,    # костыли
                         latitude=dep_hub_data['latitude'],
                         longitude=dep_hub_data['longitude'],
                         azimuth=angledeg)
        new_drone.save()

        # Отсылаем данные о созданном дроне в БД бэкенда
        backend_add_drone_url = "http://backend_IP/api/drones"
        drone_dict = {'board_number': new_drone.id,
                      'type': new_drone.type,
                      'capacity': new_drone.capacity,
                      'speed': new_drone.speed,
                      'latitude': new_drone.latitude,
                      'longitude': new_drone.longitude,
                      'azimuth': new_drone.azimuth}
        drone_data = json.dumps(drone_dict)
        json.loads(requests.post(backend_add_drone_url, json=drone_data))

        # Обновляем данные по перевозимым дроном заказам в БД бэкенда и сохраняем маршруты в локальную БД
        backend_order_update_url = "http://backend_IP/api/orders/"
        for order in delivery_data['orders']:
            order_data_to_update = {'bpla': new_drone.id,
                                    'dep_hub_id': delivery_data['departure_hub_id'],
                                    'dest_hub_id': delivery_data['destination_hub_id']}
            order_data = json.dumps(order_data_to_update)
            json.loads(requests.update(backend_order_update_url + str(order[0]), json=order_data))
            new_order = ORDER(backend_id=order[0],
                              track=order[1])
            new_order.save()


def manage_drones(request):
    # Поочередно обрабатывает обновления всех дронов и отправляет обновленную информацию на бэкенд. По прилету дрона
    # требуется отправить хабу отправки и хабу прилета оповещения об окончании полета (IP хабов нужно будет взять
    # из локальной БД)
    while True:
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

