from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Order
from .serializers import OrderSerializer
from accounts.permissions import IsSuperAdmin, IsRestaurantAdmin, IsAdminOrSuperAdmin
from rest_framework.permissions import IsAuthenticated, AllowAny
from restaurants.models import Restaurant

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    
    def get_permissions(self):
        # Allow chatbot to create orders without authentication
        if self.action == 'create':
            permission_classes = [AllowAny]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminOrSuperAdmin]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_superadmin:
            return Order.objects.all()
        elif user.is_restaurant_admin:
            return Order.objects.filter(restaurant=user.restaurant)
        return Order.objects.none()
    
    def perform_create(self, serializer):
        # For authenticated users (admins)
        if self.request.user.is_authenticated:
            if self.request.user.is_restaurant_admin:
                serializer.save(restaurant=self.request.user.restaurant)
            else:
                serializer.save()
        # For chatbot (unauthenticated)
        else:
            restaurant_id = self.request.data.get('restaurant_id')
            if restaurant_id:
                try:
                    restaurant = Restaurant.objects.get(id=restaurant_id)
                    serializer.save(restaurant=restaurant)
                except Restaurant.DoesNotExist:
                    raise serializer.ValidationError({'restaurant_id': 'Restaurant not found'})
            else:
                raise serializer.ValidationError({'restaurant_id': 'This field is required for chatbot orders'})
    
    def create(self, request, *args, **kwargs):
        """
        Create a new order - accessible by chatbot without authentication
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
