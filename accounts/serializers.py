from rest_framework import serializers
from django.contrib.auth import get_user_model
from restaurants.serializers import RestaurantSerializer

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role']
class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password']
    
    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        return value
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)

        user.save()
        return user
    
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)




# accounts/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from restaurants.models import Restaurant

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    # User fields
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    password = serializers.CharField(write_only=True, min_length=6)

    # Restaurant fields
    restaurant_name = serializers.CharField(max_length=255)
    restaurant_phone = serializers.CharField(max_length=20)
    restaurant_address = serializers.CharField(allow_blank=True, required=False)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate_email(self, value):
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

    def create(self, validated_data):
        username = validated_data["username"]
        email = validated_data.get("email") or ""
        password = validated_data["password"]

        restaurant_name = validated_data["restaurant_name"]
        restaurant_phone = validated_data["restaurant_phone"]
        restaurant_address = validated_data.get("restaurant_address", "")

        # Create user as admin (owner)
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role="admin",   # optional, manager already defaults to admin
        )

        # Create restaurant linked to this user
        restaurant = Restaurant.objects.create(
            owner=user,
            name=restaurant_name,
            phone=restaurant_phone,
            address=restaurant_address,
        )

        # Attach for use in response
        self.user = user
        self.restaurant = restaurant
        return user

    def to_representation(self, instance):
        # instance is User
        restaurant = getattr(self, "restaurant", None) or getattr(
            instance, "owned_restaurants", None
        )

        return {
            "user": {
                "id": instance.id,
                "username": instance.username,
                "email": instance.email,
                "role": instance.role,
            },
            "restaurant": {
                "id": restaurant.id if restaurant else None,
                "name": restaurant.name if restaurant else None,
                "phone": restaurant.phone if restaurant else None,
                "address": restaurant.address if restaurant else None,
            },
        }
