from django.urls import path
from . import views
import ast

urlpatterns = [
    path('orders', views.create_drone),
    path('drones', views.manage_drones)
]

