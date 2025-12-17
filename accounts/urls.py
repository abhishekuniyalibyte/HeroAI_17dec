from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet,LoginDemoView,RegisterDemoView,RegisterAPIView,LogoutAPIView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView
    
)
from accounts import views
router = DefaultRouter()
router.register(r'users', UserViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('login/',views.LoginView.as_view(),name='login'),  
    path("register-demo/", RegisterDemoView.as_view(), name="accounts-register-demo"),

    # DRF API
    path("register/", RegisterAPIView.as_view(), name="accounts-register"),
    path("logout/", LogoutAPIView.as_view(), name="api-logout"),

]






