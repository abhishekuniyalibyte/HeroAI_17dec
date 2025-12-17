from rest_framework import permissions
from rest_framework.permissions import BasePermission
from restaurants.models import Restaurant
from menu.models import MenuItem  # if you need it

class IsSuperAdmin(permissions.BasePermission):
    """
    Permission to only allow super admins to access the view.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'superadmin'

class IsAdmin(permissions.BasePermission):
    """
    Permission to only allow admins to access the view.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'

class IsAdminOrSuperAdmin(permissions.BasePermission):
    """
    Permission to allow both admins and super admins to access the view.
    """                 
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['admin','superadmin']

class IsRestaurantAdmin(permissions.BasePermission):
    """
    Permission to only allow admins to access their own restaurant data.
    """
    def has_object_permission(self, request, view, obj):
        # Allow super admins full access
        if request.user.role == 'superadmin':
            return True
        
        # For restaurant objects
        if hasattr(obj, 'admins'):
            return request.user in obj.admins.all()
        
        # For user objects
        if hasattr(obj, 'restaurant') and hasattr(request.user, 'restaurant'):
            return obj.restaurant == request.user.restaurant
        return False
    

class IsOwnerOrSuperAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        # superadmin (or Django superuser) can do anything
        if getattr(request.user, "role", "") == "superadmin" or getattr(request.user, "is_superuser", False):
            return True

        # Restaurant objects: must own it
        if isinstance(obj, Restaurant):
            return obj.owner_id == request.user.id

        # MenuItem objects (if you use this elsewhere): must own the parent restaurant
        if isinstance(obj, MenuItem):
            return obj.restaurant.owner_id == request.user.id

        return False
