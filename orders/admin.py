from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "restaurant", "status", "payment_status", "total", "created_at")
    list_filter = ("restaurant", "status", "payment_status", "order_type")
    inlines = [OrderItemInline]
