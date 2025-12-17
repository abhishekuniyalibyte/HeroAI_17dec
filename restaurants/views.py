# restaurants/views.py
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status

from accounts.permissions import IsOwnerOrSuperAdmin
from .models import Restaurant, RestaurantMenuImage, RestaurantMenuPDF
from .serializers import RestaurantSerializer, RestaurantMenuUploadSerializer
from .tasks import extract_menu_for_restaurant_task


class MenuPDFUploadDemoView(TemplateView):
    template_name = "menu_pdf_upload_demo.html"


class RestaurantViewSet(viewsets.ModelViewSet):
    serializer_class = RestaurantSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions, IsOwnerOrSuperAdmin]

    def get_queryset(self):
        user = self.request.user
        if getattr(user, "is_superadmin", False) or getattr(user, "role", "") == "superadmin":
            return Restaurant.objects.all()
        return Restaurant.objects.filter(owner=user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class UploadAPIView(APIView):
    """
    Upload menu images/PDFs, REPLACE old assets, trigger extraction.
    """
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated, IsOwnerOrSuperAdmin]
    serializer_class = RestaurantMenuUploadSerializer

    def post(self, request):
        restaurant = get_object_or_404(Restaurant, owner=request.user)
        self.check_object_permissions(request, restaurant)

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        image_files = data.get("menu_images") or []
        pdf_files = []

        single_pdf = data.get("menu_pdf")
        if single_pdf is not None:
            pdf_files.append(single_pdf)

        pdf_files.extend(data.get("menu_pdfs") or [])

        # delete old assets
        for img in restaurant.menu_images.all():
            if img.image:
                img.image.delete(save=False)
            img.delete()

        for pdf in restaurant.menu_pdfs.all():
            if pdf.pdf:
                pdf.pdf.delete(save=False)
            pdf.delete()

        # save new assets
        for idx, f in enumerate(image_files):
            RestaurantMenuImage.objects.create(
                restaurant=restaurant,
                image=f,
                sort_order=idx,
            )

        for f in pdf_files:
            RestaurantMenuPDF.objects.create(
                restaurant=restaurant,
                pdf=f,
            )

        # trigger extraction
        extract_menu_for_restaurant_task.delay(restaurant.id)

        return Response(
            {
                "restaurant_id": restaurant.id,
                "images_uploaded": len(image_files),
                "pdfs_uploaded": len(pdf_files),
                "detail": "Files uploaded successfully. Menu extraction started in background.",
            },
            status=status.HTTP_202_ACCEPTED,
        )
