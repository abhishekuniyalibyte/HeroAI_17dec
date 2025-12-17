from django.urls import path
from .views import (
    MenuChatAPIView,
    SimpleChatbotView,
    ChatbotWidgetDemoView,
    CategoryListView,
    PublicWidgetView,
    WidgetSettingsApiView,
    WidgetSettingsPageView,
    MenuChatFrontendView,
)

urlpatterns = [
    path("simple/", SimpleChatbotView.as_view(), name="chatbot-simple"),
    path("widget-demo/", ChatbotWidgetDemoView.as_view(), name="chatbot-demo-ui"),
    path("categories/", CategoryListView.as_view(), name="chatbot_categories"),

    # PUBLIC WIDGET
    path("widget/", PublicWidgetView.as_view(), name="public-widget"),

    # DASHBOARD + WIDGET SETTINGS
    path(
        "dashboard/widget/",
        WidgetSettingsApiView.as_view(),
        name="widget-settings-api",
    ),
    path(
        "dashboard/widget/show/",
        WidgetSettingsPageView.as_view(),
        name="widget-settings-page",   # 👈 this is what we'll use in the template
    ),

    path("chatui/", MenuChatFrontendView.as_view(), name="widget-demo"),
    path("chat/", MenuChatAPIView.as_view(), name="menu_chat_drf"),
]
