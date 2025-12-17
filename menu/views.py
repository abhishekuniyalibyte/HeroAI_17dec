# menu/views.py
from django.views.generic import TemplateView

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication

from django.db.models import Count

from restaurants.models import Restaurant
from .models import MenuItem, Category, MenuSection
from .serializers import MenuItemSerializer, CategorySerializer, MenuSectionSerializer
from .services import normalize_name


class ApiDemoView(TemplateView):
    template_name = "api_demo.html"


class MenuItemViewSet(viewsets.ModelViewSet):
    serializer_class = MenuItemSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication, SessionAuthentication]

    def _get_restaurant(self):
        user = self.request.user
        restaurant_id = self.request.query_params.get("restaurant_id")

        if getattr(user, "is_superuser", False) or getattr(user, "is_superadmin", False):
            if restaurant_id:
                try:
                    return Restaurant.objects.get(id=restaurant_id)
                except Restaurant.DoesNotExist:
                    raise ValidationError({"detail": "Restaurant not found."})

            owned = Restaurant.objects.filter(owner=user).first()
            if owned:
                return owned

            raise ValidationError({"detail": "Superadmin: provide ?restaurant_id or own a restaurant."})

        restaurant = Restaurant.objects.filter(owner=user).first()
        if not restaurant:
            raise ValidationError({"detail": "This user is not linked to any restaurant."})

        if restaurant_id and str(restaurant.id) != restaurant_id:
            raise ValidationError({"detail": "You are not allowed to access this restaurant."})

        return restaurant

    def get_queryset(self):
        restaurant = self._get_restaurant()
        return (
            MenuItem.objects
            .filter(restaurant=restaurant, is_active=True)
            .select_related("category", "menu_section")
            .order_by("category__position", "menu_section__position", "position", "name")
        )

    def perform_create(self, serializer):
        restaurant = self._get_restaurant()
        instance = serializer.save(restaurant=restaurant)

        if instance.name:
            new_norm = normalize_name(instance.name)
            if new_norm != instance.normalized_name:
                instance.normalized_name = new_norm
                instance.save(update_fields=["normalized_name"])

        return instance

    def perform_update(self, serializer):
        instance = serializer.save()
        if instance.name:
            new_norm = normalize_name(instance.name)
            if new_norm != instance.normalized_name:
                instance.normalized_name = new_norm
                instance.save(update_fields=["normalized_name"])
        return instance


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication, SessionAuthentication]

    def get_queryset(self):
        user = self.request.user
        restaurant_id = self.request.query_params.get("restaurant_id")

        if getattr(user, "is_superuser", False) or getattr(user, "is_superadmin", False):
            if restaurant_id:
                return Category.objects.filter(restaurant_id=restaurant_id, is_active=True).order_by("position", "name")
            owned = Restaurant.objects.filter(owner=user).first()
            if owned:
                return Category.objects.filter(restaurant=owned, is_active=True).order_by("position", "name")
            return Category.objects.none()

        restaurant = Restaurant.objects.filter(owner=user).first()
        if not restaurant:
            return Category.objects.none()
        return Category.objects.filter(restaurant=restaurant, is_active=True).order_by("position", "name")


class MenuSectionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MenuSectionSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication, SessionAuthentication]

    def get_queryset(self):
        user = self.request.user
        restaurant_id = self.request.query_params.get("restaurant_id")

        qs = MenuSection.objects.select_related("category", "restaurant").filter(is_active=True)

        if getattr(user, "is_superuser", False) or getattr(user, "is_superadmin", False):
            if restaurant_id:
                return qs.filter(restaurant_id=restaurant_id).order_by("category__position", "position", "name")
            owned = Restaurant.objects.filter(owner=user).first()
            if owned:
                return qs.filter(restaurant=owned).order_by("category__position", "position", "name")
            return MenuSection.objects.none()

        restaurant = Restaurant.objects.filter(owner=user).first()
        if not restaurant:
            return MenuSection.objects.none()
        return qs.filter(restaurant=restaurant).order_by("category__position", "position", "name")


class RestaurantMenuViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public endpoint: /menu/restaurants/<id>/menu-items/
    """
    serializer_class = MenuItemSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        restaurant_id = self.kwargs.get("restaurant_id")
        if not Restaurant.objects.filter(id=restaurant_id).exists():
            return MenuItem.objects.none()

        return (
            MenuItem.objects
            .filter(restaurant_id=restaurant_id, available=True, is_active=True)
            .select_related("category", "menu_section")
            .order_by("category__position", "menu_section__position", "position", "name")
        )


# OPTIONAL: widget stats helper (FK-safe example)
def category_stats_for_restaurant(restaurant_id: int):
    qs = MenuItem.objects.filter(restaurant_id=restaurant_id, is_active=True)
    return (
        qs.exclude(category__isnull=True)
        .values("category__name")
        .annotate(count=Count("id"))
        .order_by("category__name")
    )



