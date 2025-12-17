# menu/tasks.py
from celery import shared_task
from django.conf import settings
import os

from restaurants.models import Restaurant
from menu.models import MenuItem
from menu.services import rebuild_menu_from_json
from menu.embedding_context import suspend_embedding_signals
from menu.embedding_1 import MenuEmbeddingGenerator


def get_embeddings_path(restaurant_id: int) -> str:
    return os.path.join(
        settings.MEDIA_ROOT,
        "embeddings",
        f"restaurant_{restaurant_id}_menu_embeddings.pkl",
    )


@shared_task
def regenerate_menu_embeddings_for_restaurant(restaurant_id: int) -> None:
    try:
        restaurant = Restaurant.objects.get(id=restaurant_id)
    except Restaurant.DoesNotExist:
        return

    qs = (
        MenuItem.objects
        .filter(restaurant=restaurant, is_active=True, available=True)
        .select_related("category", "menu_section")
        .order_by("id")
    )

    items = []
    for item in qs:
        items.append(
            {
                "name": item.name,
                "description": item.description or "",
                # ✅ FK -> string (very important)
                "category": (item.category.name if item.category else ""),
                # optional: embedding_1 ignores it (safe to keep)
                "menu_section": (item.menu_section.name if item.menu_section else ""),
                "price": float(item.price) if item.price is not None else None,
                "currency": item.currency or "INR",
                "ingredients": item.ingredients or [],
            }
        )

    output_path = get_embeddings_path(restaurant_id)

    if not items:
        if os.path.exists(output_path):
            os.remove(output_path)
        return

    # ✅ embedding_1 supports {"items": [...]}
    menu_data = {"items": items}

    generator = MenuEmbeddingGenerator(
        model_name="sentence-transformers/all-mpnet-base-v2"
    )
    chunks = generator.create_text_chunks(menu_data)
    generator.generate_embeddings(chunks)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    generator.save_embeddings(output_path, format="pickle")

    if hasattr(restaurant, "embeddings_file"):
        rel_path = os.path.relpath(output_path, settings.MEDIA_ROOT)
        restaurant.embeddings_file.name = rel_path
        restaurant.save(update_fields=["embeddings_file"])


@shared_task
def extract_menu_for_restaurant_task(restaurant_id: int, items_from_json: list[dict]) -> None:
    """
    Generic import task:
      - bulk rebuild (signals muted)
      - regenerate embeddings once
    """
    try:
        Restaurant.objects.get(id=restaurant_id)
    except Restaurant.DoesNotExist:
        return

    with suspend_embedding_signals():
        rebuild_menu_from_json(Restaurant.objects.get(id=restaurant_id), items_from_json)

    regenerate_menu_embeddings_for_restaurant.delay(restaurant_id)
