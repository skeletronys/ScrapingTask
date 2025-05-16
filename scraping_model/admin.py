from django.contrib import admin
from .models import Car

@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'price_usd', 'odometer', 'username',
        'phone_number', 'car_number', 'car_vin', 'datetime_found'
    )
    search_fields = ('title', 'car_number', 'car_vin', 'username')
    list_filter = ('price_usd',)
