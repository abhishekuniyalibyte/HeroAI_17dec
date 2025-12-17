# backoffice/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    super_admin_dashboard,
    owner_dashboard,
    owner_menu_items_list,
    OwnerMenuItemViewSet,
    OwnerCategoryListAPIView, 
    owner_menu_categories_list
)

app_name = "backoffice"

router = DefaultRouter()
router.register(
    r"owner/api/menu-items",
    OwnerMenuItemViewSet,
    basename="owner-menu-items",
)

urlpatterns = [
    # ======================
    # SUPER ADMIN
    # ======================
    path(
        "dashboard/",
        super_admin_dashboard,
        name="superadmin_dashboard",
    ),

    # ======================
    # OWNER UIOwnerCategoryListAPIView
    # ======================
    path(
        "owner/dashboard/",
        owner_dashboard,
        name="owner_dashboard",
    ),
    path(
        "owner/menu/items/",
        owner_menu_items_list,
        name="owner_menu_items_list",
    ),

    # ======================
    # OWNER API (CRUD)
    # ======================
    path("", include(router.urls)),
    path("owner/categories/", OwnerCategoryListAPIView.as_view(), name="owner_categories_api"),
      path(
        "owner/menu/categories/",
        owner_menu_categories_list,
        name="owner_menu_categories_list",
    ),

]