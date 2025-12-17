# restaurants/serializers.py
from rest_framework import serializers
from django.core.exceptions import ValidationError

from .models import Restaurant


def validate_pdf(file):
    name = (file.name or "").lower()
    if not name.endswith(".pdf"):
        raise ValidationError("Only PDF files are allowed.")
    ct = getattr(file, "content_type", None)
    if ct and ct not in ("application/pdf", "application/x-pdf"):
        raise ValidationError("Invalid content type; must be PDF.")
    return file


class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = [
            "id",
            "owner",
            "name",
            "address",
            "phone",
            "logo",
            "is_active",
            "menu_extract_status",
            "menu_last_extracted_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "created_at",
            "updated_at",
            "menu_extract_status",
            "menu_last_extracted_at",
        ]


class RestaurantMenuUploadSerializer(serializers.Serializer):
    """
    Upload menu assets:
    - menu_images: list of images
    - menu_pdf: single PDF (optional)
    - menu_pdfs: list of PDFs (optional)
    """

    menu_images = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        allow_empty=True,
    )

    menu_pdf = serializers.FileField(
        write_only=True,
        required=False,
        validators=[validate_pdf],
    )

    menu_pdfs = serializers.ListField(
        child=serializers.FileField(validators=[validate_pdf]),
        required=False,
        allow_empty=True,
    )

    def validate(self, attrs):
        images = attrs.get("menu_images") or []
        single_pdf = attrs.get("menu_pdf")
        multi_pdfs = attrs.get("menu_pdfs") or []

        if not images and not single_pdf and not multi_pdfs:
            raise serializers.ValidationError("At least one image or PDF must be provided.")
        return attrs
