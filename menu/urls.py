# menu/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    MenuItemViewSet,
    CategoryViewSet,
    MenuSectionViewSet,
    RestaurantMenuViewSet,
    ApiDemoView,
)

router = DefaultRouter()
router.register(r"menu-items", MenuItemViewSet, basename="menuitem")
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"sections", MenuSectionViewSet, basename="menusection")

urlpatterns = [
    path("", include(router.urls)),
    path("demo/", ApiDemoView.as_view(), name="api-demo"),

    # public
    path("restaurants/<int:restaurant_id>/menu-items/", RestaurantMenuViewSet.as_view({"get": "list"})),
]
