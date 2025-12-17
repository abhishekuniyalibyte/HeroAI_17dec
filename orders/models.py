# orders/models.py
from decimal import Decimal

from django.db import models
from django.conf import settings

from restaurants.models import Restaurant
from menu.models import MenuItem


class Order(models.Model):
    """
    Single customer order for a restaurant.

    Used by:
      - Chatbot (via session_id for anonymous visitors)
      - Admin panel (restaurant staff)
    """

    class OrderType(models.TextChoices):
        DINEIN = "DINEIN", "Dine-in"
        TAKEAWAY = "TAKEAWAY", "Takeaway"
        DELIVERY = "DELIVERY", "Delivery"

    class OrderStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        IN_KITCHEN = "IN_KITCHEN", "In kitchen"
        READY = "READY", "Ready"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    class PaymentMethod(models.TextChoices):
        PAY_AT_COUNTER = "PAY_AT_COUNTER", "Pay at counter"
        COD = "COD", "Cash on delivery"
        ONLINE = "ONLINE", "Online (gateway)"

    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    # Which restaurant this order belongs to
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="orders",
    )

    # Who created it (optional; chatbot orders will usually be null here)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_orders",
    )

    # 🔴 Important for chatbot: anonymous visitor identifier
    session_id = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
        help_text="Anonymous chat session identifier (for chatbot visitors).",
    )

    order_type = models.CharField(
        max_length=10,
        choices=OrderType.choices,
        default=OrderType.TAKEAWAY,
        db_index=True,
    )

    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
        db_index=True,
    )

    # We are not modelling a full Customer user yet, just simple text info
    customer_name = models.CharField(max_length=100, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    delivery_address = models.TextField(blank=True)  # for DELIVERY
    table_number = models.CharField(max_length=20, blank=True)  # for DINEIN

    # Money fields
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.PAY_AT_COUNTER,
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    paid_at = models.DateTimeField(null=True, blank=True)

    # For analytics later: chatbot / admin / kiosk / website etc.
    source = models.CharField(
        max_length=20,
        default="chatbot",
        help_text="Origin of order: chatbot, admin, kiosk, etc.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["restaurant", "status"]),
            models.Index(fields=["restaurant", "session_id"]),
        ]

    def __str__(self):
        return f"Order #{self.pk} - {self.restaurant.name} - {self.status}"

    def recalc_totals(self, save: bool = True) -> None:
        """
        Recalculate subtotal/tax/total from items.
        Chatbot/service layer can call this after item changes.
        """
        subtotal = Decimal("0.00")
        for item in self.items.all():
            subtotal += item.total_price

        self.subtotal = subtotal
        self.tax = Decimal("0.00")  # later: plug in real tax logic
        self.total = self.subtotal + self.tax

        if save:
            self.save(update_fields=["subtotal", "tax", "total"])


class OrderItem(models.Model):
    """
    Line item inside an Order.
    Snapshots important fields from MenuItem so that
    later price/name changes don't affect historical orders.
    """

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )

    # Current menu item reference
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.PROTECT,  # don't allow deleting dishes used in orders
        related_name="order_items",
    )

    # Snapshot fields
    name = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    notes = models.TextField(
        blank=True,
        help_text="Special instructions: 'extra cheese', 'no onion', etc.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Order item"
        verbose_name_plural = "Order items"

    def __str__(self):
        return f"{self.quantity} x {self.name} (Order #{self.order_id})"
