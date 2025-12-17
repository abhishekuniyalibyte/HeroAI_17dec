# chatbot/views.py
import uuid
import requests
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from menu.models import MenuItem  # 👈 add this
from django.db.models import Count
from restaurants.models import Restaurant
from .serializers import ChatRequestSerializer
from .engine import parse_message
from .services import apply_intent
from orders.models import Order   # ✅ add this
from chatbot.models import RestaurantWidget
from django.db.models import Count, F
from django.utils import timezone
from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

class WidgetSettingsPageView(TemplateView):
    template_name = "widget_settings.html"


from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication

from django.conf import settings

from restaurants.models import Restaurant
from .models import RestaurantWidget  # jahan bhi defined hai


class WidgetSettingsApiView(APIView):
    """
    API endpoint (JWT protected) that returns:
    - restaurant info (including logo_url)
    - widget token
    - iframe URL
    - iframe embed snippets
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def _build_logo_url(self, request, restaurant):
        """
        Helper to build absolute logo URL (or None if no logo).
        """
        if restaurant.logo and hasattr(restaurant.logo, "url"):
            # absolute URL banane ke liye request ka use
            return request.build_absolute_uri(restaurant.logo.url)
        return None

    def get(self, request, *args, **kwargs):
        restaurant = Restaurant.objects.filter(owner=self.request.user).first()
        if not restaurant:
            return Response(
                {"detail": "You are not linked to any restaurant."},
                status=status.HTTP_403_FORBIDDEN,
            )

        widget, _ = RestaurantWidget.objects.get_or_create(restaurant=restaurant)

        base_url = getattr(settings, "PUBLIC_BASE_URL", "").rstrip("/")
        iframe_src = widget.iframe_src  # e.g. f"{base_url}/widget/?token=...."

        # Option 1: simple inline iframe (floating bubble style)
        script_snippet = f"""
<iframe
  src="{iframe_src}"
  style="position: fixed;
         bottom: 20px;
         right: 20px;
         width: 380px;
         height: 600px;
         border: 0;
         border-radius: 16px;
         z-index: 999999;">
</iframe>
""".strip()

        # Option 2: iframe block (for embedding inside page layout)
        iframe_snippet = f"""
<iframe
  src="{iframe_src}"
  style="width: 100%;
         max-width: 420px;
         height: 600px;
         border: 0;
         border-radius: 16px;">
</iframe>
""".strip()

        logo_url = self._build_logo_url(request, restaurant)
        qs = MenuItem.objects.filter(restaurant=restaurant, is_active=True)

        category_stats = (
            qs.exclude(category__isnull=True)
            .exclude(category__name__isnull=True)
            .exclude(category__name__exact="")
            .values(category_name=F("category__name"))
            .annotate(count=Count("id"))
            .order_by("category_name")
        )


        return Response(
            {
                "restaurant": {
                    "id": restaurant.id,
                    "name": restaurant.name,
                    "logo_url": logo_url,
                },
                "widget": {
                    "public_token": widget.public_token,
                    "is_active": widget.is_active,
                    "iframe_src": iframe_src,
                },
                "snippets": {
                    "script": script_snippet,
                    "iframe": iframe_snippet,
                },
                "menu_summary": {
                    "categories": list(category_stats),
                },
            },
            status=status.HTTP_200_OK,
        )


from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt

@method_decorator(xframe_options_exempt, name="dispatch")
class PublicWidgetView(TemplateView):
    """
    Public iframe page: /widget/?token=XXX
    """
    template_name = "menu_chat_frontend.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        token = self.request.GET.get("token")

        widget = get_object_or_404(
            RestaurantWidget,
            public_token=token,
            is_active=True,
        )
        ctx["restaurant"] = widget.restaurant
        return ctx




class ChatbotWidgetDemoView(TemplateView):
    template_name = "chatbot_widget_demo.html"


@method_decorator(csrf_exempt, name="dispatch")
class SimpleChatbotView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        restaurant_id = serializer.validated_data["restaurant_id"]
        session_id = serializer.validated_data.get("session_id") or ""
        message = serializer.validated_data["message"]

        restaurant = get_object_or_404(Restaurant, id=restaurant_id)
        if not session_id:
            session_id = f"sess_{uuid.uuid4().hex[:16]}"

        # 1️⃣ Parse message → intent
        result = parse_message(message)

        # 2️⃣ Handle CONFIRM_ORDER intent separately (payment trigger)
        if result.intent == "CONFIRM_ORDER":
            order = Order.objects.filter(
                restaurant=restaurant,
                session_id=session_id,
                status=Order.OrderStatus.PENDING,
            ).first()

            if not order:
                return Response(
                    {"reply": "No open order found to confirm.", "session_id": session_id},
                    status=status.HTTP_200_OK,
                )

            payments_api = request.build_absolute_uri("/api/payments/create/")
            try:
                r = requests.post(payments_api, json={"order_id": order.id})
                if r.status_code != 200:
                    # Razorpay create failed → reply politely instead of KeyError
                    msg = r.json().get("detail", "Unable to create payment.")
                    return Response(
                        {
                            "reply": f"⚠️ Cannot process payment — there should be atleast one order.",
                            "session_id": session_id,
                        },
                        status=status.HTTP_200_OK,
                    )

                data = r.json()

                return Response(
                    {
                        "reply": "Please complete your payment to confirm the order.",
                        "session_id": session_id,
                        "payment": {
                            "key": data["key"],
                            "order_id": data["razorpay_order_id"],
                            "amount": data["amount"],
                            "currency": data["currency"],
                        },
                    },
                    status=status.HTTP_200_OK,
                )
            except Exception as e:
                print("Payment creation error:", e)
                return Response(
                    {"reply": "Something went wrong creating the payment."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )


        # 3️⃣ For all other intents → process normally
                # 3️⃣ For all other intents → process normally
        reply_text, order, extra = apply_intent(restaurant, session_id, result)

        # 4️⃣ Prepare order snapshot
        items_data = [
            {
                "id": item.menu_item.id,
                "name": item.name,
                "quantity": item.quantity,
                "unit_price": str(item.unit_price),
                "total_price": str(item.total_price),
            }
            for item in order.items.select_related("menu_item").all()
        ]

        order_data = {
            "id": order.id,
            "status": order.status,
            "subtotal": str(order.subtotal),
            "tax": str(order.tax),
            "total": str(order.total),
            "items": items_data,
        }

        # 5️⃣ Return chat response (+ any extra UI payload like menu_items)
        payload = {
            "reply": reply_text,
            "session_id": session_id,
            "order": order_data,
        }
        if extra:
            payload.update(extra)

        return Response(payload, status=status.HTTP_200_OK)


# class PopularItemsView(APIView):
#     """
#     Returns a list of most-ordered menu items for a restaurant.

#     GET /api/chatbot/popular-items/?restaurant_id=1

#     Response:
#     {
#         "items": [
#             {"id": 12, "name": "Masala Dosa"},
#             {"id": 5, "name": "Paneer Butter Masala"},
#             ...
#         ]
#     }
#     """
#     permission_classes = [AllowAny]
#     authentication_classes = []

#     def get(self, request, *args, **kwargs):
#         restaurant_id = request.query_params.get("restaurant_id")
#         if not restaurant_id:
#             return Response(
#                 {"detail": "restaurant_id is required"},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#         restaurant = get_object_or_404(Restaurant, id=restaurant_id)

#         # Aggregate by MenuItem, ordered by total quantity ordered (most popular first)
#         qs = (
#             OrderItem.objects
#             .filter(order__restaurant=restaurant)
#             .values("menu_item_id", "menu_item__name")
#             .annotate(total_qty=Sum("quantity"))
#             .order_by("-total_qty")[:6]   # top 6
#         )

#         items = [
#             {
#                 "id": row["menu_item_id"],
#                 "name": row["menu_item__name"],
#             }
#             for row in qs
#             if row["menu_item_id"] is not None
#         ]

#         return Response({"items": items}, status=status.HTTP_200_OK)


class CategoryListView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        restaurant_id = request.query_params.get("restaurant_id")
        if not restaurant_id:
            return Response({"detail": "restaurant_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        restaurant = get_object_or_404(Restaurant, id=restaurant_id)

        qs = (
            MenuItem.objects.filter(
                restaurant=restaurant,
                available=True,
                is_active=True,   # (optional but recommended if you use it)
            )
            .exclude(category__isnull=True)
            .exclude(category__name__isnull=True)
            .exclude(category__name__exact="")
            .values_list("category__name", flat=True)   # ✅ return names
            .distinct()
            .order_by("category__name")
        )

        return Response({"categories": list(qs)}, status=status.HTTP_200_OK)










##################################################################################################################################






class MenuChatFrontendView(TemplateView):
    """
    Simple page that just loads the chat widget UI (no backend API).
    """
    template_name = "menu_chat_frontend.html"
    
# chatbot/views.py

import os
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView

from .serializers import MenuChatRequestSerializer
from menu.tasks import get_embeddings_path  # helper jo embeddings path deta hai

import os
from .chatbott import MenuChatbot
from menu.tasks import get_embeddings_path

CHATBOT_CACHE: dict[int, dict] = {}


def get_chatbot_for_restaurant(restaurant_id: int) -> MenuChatbot:
    """
    Har restaurant ke liye ek hi MenuChatbot instance banega,
    lekin agar embeddings file update ho jaaye to auto-reload ho jaayega.
    """
    embeddings_path = get_embeddings_path(restaurant_id)

    if not os.path.exists(embeddings_path):
        raise FileNotFoundError(
            f"Embeddings file not found for restaurant {restaurant_id}: {embeddings_path}"
        )

    # current file ka modified time
    current_mtime = os.path.getmtime(embeddings_path)  # isse file ka last modified time mil jayega jisse hum compare karenge 

    # 1) Cache hit + file unchanged → purana bot use karo
    if restaurant_id in CHATBOT_CACHE:
        entry = CHATBOT_CACHE[restaurant_id]
        bot = entry["bot"]
        cached_mtime = entry["mtime"]

        if cached_mtime == current_mtime:
            print(
                f"[chatbot-cache] HIT | restaurant_id={restaurant_id} | mtime={current_mtime}"
            )
            return bot

        # 2) Cache hit, lekin file change ho chuki → reload karna padega
        print(
            f"[chatbot-cache] STALE | restaurant_id={restaurant_id} | "
            f"old_mtime={cached_mtime} new_mtime={current_mtime} → reloading MenuChatbot"
        )

    else:
        print(
            f"[chatbot-cache] MISS for restaurant {restaurant_id} → creating new MenuChatbot"
        )

    # yahan aaoge agar:
    # - ya to first time call hai
    # - ya embeddings file update ho gayi hai
    bot = MenuChatbot(embeddings_path)

    CHATBOT_CACHE[restaurant_id] = {
        "bot": bot,
        "mtime": current_mtime,
    }

    return bot



class MenuChatAPIView(GenericAPIView):
    """
    DRF CBV:
    - Browsable API se HTML form mil jaayega (serializer ke basis pe)
    - POST: {message, restaurant_id} leke reply return karega
    """

    serializer_class = MenuChatRequestSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user_message = serializer.validated_data["message"].strip()
        restaurant_id = serializer.validated_data["restaurant_id"]

        if not user_message:
            return Response(
                {"message": ["This field may not be blank."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            bot = get_chatbot_for_restaurant(restaurant_id)
            
        except FileNotFoundError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)

        reply = bot.chat(user_message)
        return Response({"reply": reply}, status=status.HTTP_200_OK)





