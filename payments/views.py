# payments/views.py
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

import json
import razorpay

from orders.models import Order
from .models import Payment


# Initialize Razorpay client
client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)


# -------------------------
# 1) CREATE PAYMENT (DRF)
# -------------------------
@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def create_payment(request):
    """
    Create Razorpay order and DB record for a given restaurant order.
    """
    order_id = request.data.get("order_id")
    if not order_id:
        return Response(
            {"detail": "order_id is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    order = get_object_or_404(Order, id=order_id)
    amount_paise = int(order.total * 100)

    # 🧩 Guard: don't create Razorpay order if total ≤ 0
    if amount_paise < 100:  # minimum ₹1.00
        return Response(
            {"detail": "Order amount must be at least ₹1.00"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ✅ Create Razorpay order
    try:
        razorpay_order = client.order.create(
            {"amount": amount_paise, "currency": "INR", "payment_capture": 1}
        )
    except Exception as e:
        print("Razorpay create error:", e)
        return Response(
            {"detail": f"Payment creation failed: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ✅ Create/Update Payment record
    payment, _ = Payment.objects.update_or_create(
        order=order,
        defaults={
            "razorpay_order_id": razorpay_order["id"],
            "amount": amount_paise,
            "status": "CREATED",
        },
    )

    return Response(
        {
            "key": settings.RAZORPAY_KEY_ID,
            "razorpay_order_id": razorpay_order["id"],
            "amount": amount_paise,
            "currency": "INR",
        },
        status=status.HTTP_200_OK,
    )

# -------------------------
# 2) VERIFY PAYMENT (plain Django)
# -------------------------
@csrf_exempt
def verify_payment(request):
    """
    Verify Razorpay payment signature and update DB records.

    Request JSON (from frontend handler):
        {
          "razorpay_payment_id": "...",
          "razorpay_order_id": "...",
          "razorpay_signature": "..."
        }

    Response JSON:
        { "status": "success" }  or { "status": "failure", "detail": "..." }
    """
    if request.method != "POST":
        return JsonResponse(
            {"status": "failure", "detail": "Only POST allowed"},
            status=405,
        )

    # Parse JSON safely
    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {"status": "failure", "detail": "Invalid JSON"},
            status=400,
        )

    rzp_order_id = data.get("razorpay_order_id")
    rzp_payment_id = data.get("razorpay_payment_id")
    rzp_signature = data.get("razorpay_signature")

    if not (rzp_order_id and rzp_payment_id and rzp_signature):
        return JsonResponse(
            {"status": "failure", "detail": "Missing payment parameters"},
            status=400,
        )

    try:
        # 1️⃣ Verify signature with Razorpay
        client.utility.verify_payment_signature({
            "razorpay_order_id": rzp_order_id,
            "razorpay_payment_id": rzp_payment_id,
            "razorpay_signature": rzp_signature,
        })

        # 2️⃣ Update Payment record
        payment = Payment.objects.get(razorpay_order_id=rzp_order_id)
        payment.razorpay_payment_id = rzp_payment_id
        payment.razorpay_signature = rzp_signature
        payment.status = "SUCCESS"
        payment.save(update_fields=[
            "razorpay_payment_id", "razorpay_signature", "status"
        ])

        # 3️⃣ Update linked Order (confirmed + paid)
        order = payment.order
        order.status = Order.OrderStatus.CONFIRMED

        # 🟢 Also mark payment_status as PAID if field exists
        if hasattr(order, "payment_status"):
            try:
                # enum field like Order.PaymentStatus.PAID
                order.payment_status = order.PaymentStatus.PAID
            except AttributeError:
                # fallback string
                order.payment_status = "PAID"

        order.save(update_fields=["status", "payment_status"] 
                   if hasattr(order, "payment_status") else ["status"])

        return JsonResponse({"status": "success"}, status=200)

    except Exception as e:
        print("Verification failed:", e)
        return JsonResponse(
            {"status": "failure", "detail": str(e)}, status=400
        )
