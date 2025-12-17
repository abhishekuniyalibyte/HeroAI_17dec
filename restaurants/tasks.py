# restaurants/tasks.py
from celery import shared_task
from django.utils import timezone

from .models import Restaurant
from .services import run_menu_extraction_pipeline


@shared_task(bind=True, max_retries=3)
def extract_menu_for_restaurant_task(self, restaurant_id: int):
    try:
        restaurant = Restaurant.objects.get(id=restaurant_id)
    except Restaurant.DoesNotExist:
        return {"status": "error", "error": "Restaurant not found"}

    # mark pending -> processing is done inside services, but pending is useful if queued
    if restaurant.menu_extract_status in ("idle", "failed", "succeeded"):
        restaurant.menu_extract_status = "pending"
        restaurant.menu_extract_error = ""
        restaurant.save(update_fields=["menu_extract_status", "menu_extract_error"])

    success, info = run_menu_extraction_pipeline(restaurant)

    if not success:
        # services already set failed + error message
        return {"status": "error", **info}

    return {"status": "ok", **info}
