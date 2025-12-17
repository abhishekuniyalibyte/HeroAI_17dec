from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.authtoken.views import obtain_auth_token
from django.views.generic import TemplateView
from accounts.views  import LoginDemoView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/accounts/', include('accounts.urls')),
    path('api/restaurants/', include('restaurants.urls')),
    path('api/menu/', include('menu.urls')),
    path('api/orders/', include('orders.urls')),
    path('api-token-auth/', obtain_auth_token, name='api_token_auth'),
    path("api/payments/", include("payments.urls")),
    path("", LoginDemoView.as_view(), name="login-demo"), 

    path("api/chatbot/", include("chatbot.urls")),

    # demo page for your widget
    path(
        "demo-chat/",
        TemplateView.as_view(template_name="chat_demo.html"),
        name="chat-demo",
    ),
    path("super-admin/", include("backoffice.urls")),
]


if settings.DEBUG:
    # Serve static files (including chat-widget.js) from /static
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / "static")
    # Serve media uploads from /media
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

