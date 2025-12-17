# menu/admin.py
from django.contrib import admin
from .models import Category, MenuSection, MenuItem, MenuItemImage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "restaurant", "external_category_id", "is_active", "position")
    list_filter = ("restaurant", "is_active")
    search_fields = ("name", "slug", "restaurant__name", "external_category_id")
    ordering = ("restaurant", "position", "name")


@admin.register(MenuSection)
class MenuSectionAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "restaurant", "category", "external_menu_id", "is_active", "position")
    list_filter = ("restaurant", "category", "is_active")
    search_fields = ("name", "restaurant__name", "category__name", "external_menu_id")
    ordering = ("restaurant", "category__position", "position", "name")


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "restaurant",
        "category",
        "menu_section",
        "price",
        "available",
        "is_active",
        "position",
    )
    list_filter = ("restaurant", "available", "is_active", "category", "menu_section")
    search_fields = (
        "name",
        "description",
        "restaurant__name",
        "category__name",
        "menu_section__name",
        "external_item_id",
    )
    ordering = ("restaurant", "category__position", "menu_section__position", "position", "name")
    readonly_fields = ("created_at", "updated_at")

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("restaurant", "category", "menu_section")
        user = request.user

        if user.is_superuser or getattr(user, "is_superadmin", False):
            return qs
        if getattr(user, "is_restaurant_admin", False):
            return qs.filter(restaurant__owner=user)
        return qs.none()

    def has_view_permission(self, request, obj=None):
        user = request.user
        if user.is_superuser or getattr(user, "is_superadmin", False):
            return True
        if not getattr(user, "is_restaurant_admin", False):
            return False
        if obj is None:
            return True
        return obj.restaurant.owner_id == user.id

    def has_change_permission(self, request, obj=None):
        return self.has_view_permission(request, obj=obj)

    def has_add_permission(self, request):
        user = request.user
        return user.is_superuser or getattr(user, "is_superadmin", False) or getattr(user, "is_restaurant_admin", False)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj=obj)


@admin.register(MenuItemImage)
class MenuItemImageAdmin(admin.ModelAdmin):
    list_display = ("id", "menu_item", "image_url", "external_attachment_id", "created_at")
    list_filter = ("menu_item__restaurant",)
    search_fields = ("menu_item__name", "menu_item__restaurant__name", "external_attachment_id")
