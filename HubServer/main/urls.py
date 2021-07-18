from django.urls import path
from . import views

urlpatterns = [
    path('orders', views.create_drone),
    path('drones', views.manage_drones),
    path('hubs', views.manage_hubs),
    path('acceleration', views.apply_acceleration)
]

