# backoffice/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from restaurants.models import Restaurant
from accounts.models import User
from orders.models import Order
from rest_framework import permissions
from menu.models import MenuItem
from .serializers import MenuItemSerializer
from rest_framework.response import Response
from rest_framework import viewsets



def super_admin_dashboard(request):
    total_stores = Restaurant.objects.count()
    total_users = User.objects.count()
    total_orders = Order.objects.count()
    stores = Restaurant.objects.all()
    return render(request, "superadmin/dashboard.html",{"total_stores":total_stores,"total_users":total_users,"total_orders":total_orders,"stores":stores})


# @login_required
def owner_dashboard(request):
    return render(request, "owner/dashboard.html",{"active_page": "dashboard"})


def owner_menu_items_list(request):
    context = {
        "active_page": "menu_items",
    }
    
    return render(request, "owner/menu_items_list.html", context)


class OwnerMenuItemViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MenuItemSerializer

    def get_restaurant(self):
        # never crash
        return Restaurant.objects.filter(owner=self.request.user).first()

    def get_queryset(self):
        restaurant = self.get_restaurant()
        if not restaurant:
            return MenuItem.objects.none()
        qs = MenuItem.objects.filter(restaurant=restaurant)

        # optional filters
        active = self.request.query_params.get("active")  # "1" or "0"
        if active == "1":
            qs = qs.filter(is_active=True)
        elif active == "0":
            qs = qs.filter(is_active=False)

        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(name__icontains=q)

        return qs.order_by("name")

    def perform_create(self, serializer):
        restaurant = self.get_restaurant()
        if not restaurant:
            raise permissions.PermissionDenied("Restaurant not found for this user.")
        serializer.save(restaurant=restaurant)

    # ✅ Soft delete instead of hard delete (recommended)
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)

# menu/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from restaurants.models import Restaurant
from menu.models import Category
from .serializers import CategorySerializer

def owner_menu_categories_list(request):
    restaurant = Restaurant.objects.filter(owner=request.user).first()

    return render(
        request,
        "owner/menu_categories_list.html",
        {
            "restaurant": restaurant,
            "active_page": "menu_categories",
        },
    )


class OwnerCategoryListAPIView(APIView):
    """
    GET /api/menu/categories/
    Owner-only: returns categories of owner's restaurant
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        restaurant = Restaurant.objects.filter(owner=request.user).first()
        if not restaurant:
            return Response({"results": []})

        qs = Category.objects.filter(restaurant=restaurant,is_active=True)

        # 🔍 search
        q = request.query_params.get("q")
        if q:
            qs = qs.filter(name__icontains=q)

        # 🔍 active filter
        active = request.query_params.get("active")
        if active in ["0", "1"]:
            qs = qs.filter(is_active=bool(int(active)))

        qs = qs.order_by("name")

        serializer = CategorySerializer(
            qs,
            many=True,
            context={"request": request},
        )
        return Response({"results": serializer.data})



    