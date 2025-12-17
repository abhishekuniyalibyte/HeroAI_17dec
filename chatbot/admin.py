from django.contrib import admin

# Register your models here.
# chatbot/admin.py
from django.contrib import admin
from .models import RestaurantWidget


class SuperuserOnlyAdmin(admin.ModelAdmin):
    """
    This ModelAdmin makes the model visible + editable
    ONLY for Django superusers (is_superuser=True).
    """

    list_display = ("restaurant", "public_token", "is_active", "created_at", "updated_at")
    readonly_fields = ("public_token", "created_at", "updated_at")
    search_fields = ("restaurant__name", "public_token")
    list_filter = ("is_active", "created_at")

    # Hide the whole model from non-superusers in the left sidebar
    def has_module_permission(self, request):
        return bool(request.user and request.user.is_superuser)

    # View permission
    def has_view_permission(self, request, obj=None):
        return bool(request.user and request.user.is_superuser)

    # Add permission
    def has_add_permission(self, request):
        return bool(request.user and request.user.is_superuser)

    # Change permission
    def has_change_permission(self, request, obj=None):
        return bool(request.user and request.user.is_superuser)

    # Delete permission
    def has_delete_permission(self, request, obj=None):
        return bool(request.user and request.user.is_superuser)


admin.site.register(RestaurantWidget, SuperuserOnlyAdmin)
