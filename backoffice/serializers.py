from rest_framework import serializers 
from menu.models import MenuItem

class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = [
            "id",
            "name",
            "category",
            "price",
            "available",
            "is_active",
            "currency",
        ]
        
# menu/serializers.py
from rest_framework import serializers
from menu.models import Category

class CategorySerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "is_active",
            "created_at",
            "image_url",
        ]

    def get_image_url(self, obj):
        request = self.context.get("request")

        # If your Category model DOES NOT have image field:
        image = getattr(obj, "image", None)  # safe
        if image and hasattr(image, "url") and request:
            return request.build_absolute_uri(image.url)

        return None

        