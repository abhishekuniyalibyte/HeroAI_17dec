# restaurants/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import RestaurantViewSet, UploadAPIView, MenuPDFUploadDemoView

router = DefaultRouter()
router.register(r"restaurants", RestaurantViewSet, basename="restaurant")

urlpatterns = [
    path("", include(router.urls)),
    path("upload/", UploadAPIView.as_view(), name="restaurant-menu-upload"),
    path("upload-demo/", MenuPDFUploadDemoView.as_view(), name="menu-pdf-upload-demo"),
]

