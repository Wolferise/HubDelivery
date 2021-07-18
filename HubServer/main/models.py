from django.db import models

# Create your models here.


class ORDER(models.Model):
    backend_id = models.IntegerField(blank=True, null=True)
    bpla = models.IntegerField(blank=True, null=True)
    track = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'order'


class BPLA(models.Model):
    type = models.CharField(max_length=10)
    capacity = models.SmallIntegerField(blank=True, null=True)
    speed = models.FloatField(blank=True, null=True)
    # Здесь должны быть ссылки на хаб отправки и прилета
    latitude = models.CharField(max_length=15, null=True)
    longitude = models.CharField(max_length=15, null=True)
    azimuth = models.FloatField(blank=True, null=True)
    cur_departure = models.IntegerField(blank=True, null=True)
    cur_destination = models.IntegerField(blank=True, null=True)
    lat_delta = models.FloatField(blank=True, null=True)
    long_delta = models.FloatField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'bpla'


class HUB(models.Model):
    type = models.CharField(max_length=10)
    workload = models.FloatField(blank=True, null=True)
    latitude = models.CharField(max_length=15, null=True)
    longitude = models.CharField(max_length=15, null=True)
    ip = models.CharField(max_length=15, null=True)
    backend_id = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'hub'
