from rest_framework import serializers
from .models import Order
from restaurants.serializers import RestaurantSerializer

class OrderSerializer(serializers.ModelSerializer):
    restaurant_details = RestaurantSerializer(source='restaurant', read_only=True)
    
    class Meta:
        model = Order
        fields = ['id', 'restaurant', 'restaurant_details', 'customer_name', 
                  'phone_number', 'items', 'total_amount', 'status', 
                  'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']