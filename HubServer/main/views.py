from django.http import HttpResponse
import django
import requests
import ast
import json
from .models import BPLA, HUB, ORDER
import math
import time
from django.views.decorators.csrf import csrf_exempt

multiplier = 1


@csrf_exempt
def apply_acceleration(request):
    global multiplier
    if request.method == "POST":
        acceleration = request.POST
        multiplier = acceleration['multiplier']
        return HttpResponse('success')


@csrf_exempt
def create_drone(request):
    if request.method == "POST":
        delivery_data = request.POST
        print(delivery_data)
        try:
            error_check = delivery_data['destination_hub_id']
        except django.utils.datastructures.MultiValueDictKeyError:
            orders = ast.literal_eval(delivery_data['orders'])
            for order in orders:
                print("order", order, "finished!")
            return HttpResponse("<h1>No destination hub hub</h1>")
        # Загружаем данные о хабе отправления и прибытия
        backend_dep_url = "http://26.77.72.147:8080/api/hubs/" + str(delivery_data['departure_hub_id'])
        dep_hub_data = ast.literal_eval(requests.get(backend_dep_url).content.decode('UTF-8'))
        backend_dest_url = "http://26.77.72.147:8080/api/hubs/" + str(delivery_data['destination_hub_id'])
        dest_hub_data = ast.literal_eval(requests.get(backend_dest_url).content.decode('UTF-8'))

        # создаем хабы в БД, если их там еще нет
        if not HUB.objects.filter(backend_id=dep_hub_data['id']).exists():
            new_hub = HUB(type=dep_hub_data['type'],
                          workload=dep_hub_data['workload'],
                          latitude=dep_hub_data['latitude'],
                          longitude=dep_hub_data['longitude'],
                          backend_id=dep_hub_data['id'])
            new_hub.save()
        if not HUB.objects.filter(backend_id=dest_hub_data['id']).exists():
            new_hub = HUB(type=dest_hub_data['type'],
                          workload=dest_hub_data['workload'],
                          latitude=dest_hub_data['latitude'],
                          longitude=dest_hub_data['longitude'],
                          backend_id=dest_hub_data['id'])
            new_hub.save()
        # Определяем тип дрона по формуле
        drone_type = min(int(dest_hub_data['type']), int(dep_hub_data['type']))

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

        if drone_type == 0:
            speed = 1000
        elif drone_type == 1:
            speed = 5000
        else:
            speed = 25000

        update_frequency_per_hour = 1200
        new_lat = float(dep_hub_data['latitude']) + (speed / update_frequency_per_hour) * math.cos(
            float(angledeg) * math.pi / 180) / (6371 * math.pi / 180)
        new_long = float(dep_hub_data['longitude']) + (speed / update_frequency_per_hour) * math.sin(
            float(angledeg) * math.pi / 180) / math.cos(float(dep_hub_data['latitude']) * math.pi / 180) / (
                           6371 * math.pi / 180)

        lat_delta = new_lat - float(dep_hub_data['latitude'])
        long_delta = new_long - float(dep_hub_data['longitude'])
        # Сохраняем дрон в локальную БД
        new_drone = BPLA(type=drone_type,
                         capacity=drone_type * 500 + 500,  # костыли
                         speed=speed,  # костыли
                         latitude=dep_hub_data['latitude'],
                         longitude=dep_hub_data['longitude'],
                         cur_departure=delivery_data['departure_hub_id'],
                         cur_destination=delivery_data['destination_hub_id'],
                         azimuth=angledeg,
                         lat_delta=lat_delta,
                         long_delta=long_delta)
        new_drone.save()

        # Отсылаем данные о созданном дроне в БД бэкенда
        backend_add_drone_url = "http://26.77.72.147:8080/api/drones"
        drone_dict = {'board_number': new_drone.id,
                      'type': new_drone.type,
                      'capacity': new_drone.capacity,
                      'speed': new_drone.speed,
                      'latitude': new_drone.latitude,
                      'longitude': new_drone.longitude,
                      'azimuth': new_drone.azimuth,
                      'departure_hub': new_drone.cur_departure,
                      'destination_hub': new_drone.cur_destination,
                      'lat_delta': lat_delta,
                      'long_delta': long_delta}
        requests.post(backend_add_drone_url, data=drone_dict)

        # Обновляем данные по перевозимым дроном заказам в БД бэкенда и сохраняем маршруты в локальную БД
        backend_order_update_url = "http://26.77.72.147:8080/api/orders/"
        delivery_data = dict(delivery_data)

        for order in delivery_data['orders']:
            order = ast.literal_eval(order)
            for key, value in order.items():
                order_id = key
                order_track = value
            print(order_id)
            order_data_to_update = {'bpla': new_drone.id,
                                    'dep_hub_id': delivery_data['departure_hub_id'][0],
                                    'dest_hub_id': delivery_data['destination_hub_id'][0]}
            print(delivery_data['departure_hub_id'][0])
            order_data = json.dumps(order_data_to_update)
            requests.put(backend_order_update_url + str(order_id), json=order_data)
            new_order = ORDER(backend_id=order_id,
                              bpla=new_drone.id,
                              track=str(order_track))
            new_order.save()
    return HttpResponse("<h1>Success</h1>")


@csrf_exempt
def manage_drones(request):
    global multiplier
    # Поочередно обрабатывает обновления всех дронов и отправляет обновленную информацию на бэкенд. По прилету дрона
    # требуется отправить хабу отправки и хабу прилета оповещения об окончании полета (IP хабов нужно будет взять
    # из локальной БД)
    if request.method == "DELETE":
        drones = BPLA.objects.all()
        drones.delete()
        backend_add_drone_url = "http://26.77.72.147:8080/api/drones"
        requests.delete(backend_add_drone_url, json={})
        return HttpResponse("<h1>Success</h1>")
    else:
        drones_to_delete_array = []
        while True:
            # Для каждого активного дрона в локальной БД
            ttt = time.time()
            drones = BPLA.objects.all()
            update_dict = dict()
            delete_dict = dict()
            for drone in drones:

                # Сохраняем новые данные о дроне
                drone.latitude = float(drone.latitude) + drone.lat_delta * multiplier
                drone.longitude = float(drone.longitude) + drone.long_delta * multiplier
                drone.save()

                distance = calculate_distance((float(drone.latitude), float(drone.longitude)), (float(drone.latitude) +
                                                                                                drone.lat_delta *
                                                                                                multiplier,
                                                                                                float(
                                                                                                    drone.longitude) +
                                                                                                drone.lat_delta *
                                                                                                multiplier))
                # Отсылаем данные об обновлении дрона в БД бэкенда
                backend_add_drone_url = "http://26.77.72.147:8080/api/drones/" + str(drone.id) + "/"
                drone_dict = {drone.id: {'board_number': drone.id,
                                         'type': drone.type,
                                         'capacity': drone.capacity,
                                         'speed': drone.speed,
                                         'latitude': drone.latitude,
                                         'longitude': drone.longitude,
                                         'azimuth': drone.azimuth,
                                         'lat_delta': drone.lat_delta * multiplier,
                                         'long_delta': drone.long_delta * multiplier,
                                         'distance': distance}}
                update_dict.update(drone_dict)

                departure_hub = HUB.objects.get(backend_id=drone.cur_departure)
                destination_hub = HUB.objects.get(backend_id=drone.cur_destination)

                if calculate_distance((departure_hub.latitude, departure_hub.longitude),
                                      (drone.latitude, drone.longitude)) >= calculate_distance(
                    (departure_hub.latitude, departure_hub.longitude),
                    (destination_hub.latitude, destination_hub.longitude)):
                    url = "http://26.68.12.236:" + str(8000 + int(drone.cur_destination)) + "/api/orders"
                    orders = ORDER.objects.filter(bpla=drone.id)
                    for order in orders:
                        order_data = {'order_id': int(order.backend_id), 'order_track': order.track}
                        order_data = json.dumps(order_data)
                        test_data = requests.post(url, json=order_data)

                    print("drone", drone.id, "got to their destination hub!")
                    drones_to_delete_array.append(drone.id)
                    drone.delete()
            backend_add_drone_url = "http://26.77.72.147:8080/api/drones"
            requests.put(backend_add_drone_url, json=json.dumps(update_dict))
            delete_dict.update({'id': drones_to_delete_array})
            backend_delete_drone_url = "http://26.77.72.147:8080/api/drones"
            try:
                response = requests.delete(backend_delete_drone_url, json=json.dumps(delete_dict))
                print(response.content)
                drones_to_delete_array = []
            except requests.exceptions.ConnectionError:
                pass
            ts = time.time() - ttt
            try:
                time.sleep(3 - ts)
            except ValueError:
                pass


def calculate_distance(point1, point2):
    point1_latitude = float(point1[0]) * (math.pi / 180)
    point1_longitude = float(point1[1]) * (math.pi / 180)
    point2_latitude = float(point2[0]) * (math.pi / 180)
    point2_longitude = float(point2[1]) * (math.pi / 180)
    distance = 2 * 6371 * math.asin(
        math.sqrt(
            math.sin((point2_latitude - point1_latitude) / 2) ** 2 +
            math.cos(point1_latitude) *
            math.cos(point2_latitude) *
            (math.sin((point2_longitude - point1_longitude) / 2) ** 2)))
    return distance


@csrf_exempt
def manage_hubs(request):
    # Удаление всех данных хабов из БД
    if request.method == "DELETE":
        HUB.objects.all().delete()
        return HttpResponse("Successfully erased all hub data.")
