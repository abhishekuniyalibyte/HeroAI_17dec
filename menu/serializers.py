# menu/serializers.py
from rest_framework import serializers
from .models import MenuItem, Category, MenuSection


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "position", "is_active"]


class MenuSectionSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = MenuSection
        fields = ["id", "name", "category", "category_name", "position", "is_active"]


class MenuItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    menu_section_name = serializers.CharField(source="menu_section.name", read_only=True)

    class Meta:
        model = MenuItem
        fields = [
            "id",
            "restaurant",  # read-only attach
            "name",
            "normalized_name",
            "description",
            "category",
            "category_name",
            "menu_section",
            "menu_section_name",
            "price",
            "currency",
            "ingredients",
            "available",
            "is_active",
            "image_url",
            "position",
            "external_item_id",
            "raw_data",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "restaurant",
            "normalized_name",
            "created_at",
            "updated_at",
        ]
