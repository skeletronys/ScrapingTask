from django.db import models


# Create your models here.
class Car(models.Model):
    url = models.URLField(unique=True)
    title = models.CharField(max_length=255)
    price_usd = models.PositiveIntegerField()
    odometer = models.PositiveIntegerField()
    username = models.CharField(max_length=128)
    phone_number = models.CharField(max_length=20)
    image_url = models.URLField()
    images_count = models.PositiveIntegerField()
    car_number = models.CharField(max_length=32)
    car_vin = models.CharField(max_length=32)
    datetime_found = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
