# menu/services.py
import re
import hashlib
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils.text import slugify

from .models import MenuItem, Category, MenuSection


def normalize_name(name: str) -> str:
    if not name:
        return ""
    s = name.strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^\w\s\-&/]", "", s)
    return s.strip()


def clean_price(value):
    if value is None:
        return None
    if isinstance(value, (int, float, Decimal)):
        try:
            return Decimal(str(value))
        except Exception:
            return None
    s = str(value).strip()
    if not s:
        return None
    s = re.sub(r"[^\d.]", "", s)
    if not s:
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def _make_llm_item_id(
    restaurant_id: int,
    normalized_name: str,
    category_name: str = "",
    section_name: str = "",
) -> str:
    """
    Deterministic ID for items when POS/external id not available.
    Avoids UNIQUE constraint failures for external_item_id="".
    """
    key = f"{restaurant_id}|{normalized_name}|{category_name}|{section_name}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()  # deterministic
    return f"llm:{digest}"


def _get_or_create_category(restaurant, raw: dict) -> Category | None:
    cid = (raw.get("category_id") or raw.get("external_category_id") or "").strip()
    cname = (raw.get("category") or raw.get("category_name") or "").strip()

    if not cid and not cname:
        return None

    if not cname and cid:
        cname = cid

    defaults = {
        "name": cname,
        "slug": slugify(cname)[:255] if cname else "",
        "raw_data": raw.get("category_raw") or None,
        "is_active": True,  # ✅ reactivate category if it exists
    }

    if cid:
        obj, _ = Category.objects.update_or_create(
            restaurant=restaurant,
            external_category_id=cid,
            defaults=defaults,
        )
        return obj

    slug = slugify(cname)[:255]
    obj, _ = Category.objects.update_or_create(
        restaurant=restaurant,
        external_category_id="",
        slug=slug,
        defaults=defaults,
    )
    return obj


def _get_or_create_section(restaurant, category: Category | None, raw: dict) -> MenuSection | None:
    if not category:
        return None

    sid = (raw.get("menu_id") or raw.get("section_id") or raw.get("external_menu_id") or "").strip()
    sname = (raw.get("section") or raw.get("menu_section_name") or "").strip()

    if not sid and not sname:
        return None

    if not sname and sid:
        sname = sid

    defaults = {
        "name": sname,
        "raw_data": raw.get("section_raw") or None,
        "is_active": True,  # ✅ reactivate section if it exists
    }

    if sid:
        obj, _ = MenuSection.objects.update_or_create(
            restaurant=restaurant,
            category=category,
            external_menu_id=sid,
            defaults=defaults,
        )
        return obj

    obj, _ = MenuSection.objects.update_or_create(
        restaurant=restaurant,
        category=category,
        external_menu_id="",
        name=sname,
        defaults=defaults,
    )
    return obj


@transaction.atomic
def rebuild_menu_from_json(restaurant, items_from_json: list[dict]):
    """
    Full canonical import:
      1) archive old categories/sections/items
      2) upsert categories/sections/items found in new json (reactivate them)
    """

    # ✅ archive old menu items
    MenuItem.objects.filter(restaurant=restaurant).update(is_active=False, available=False)

    # ✅ archive old categories + sections (IMPORTANT)
    Category.objects.filter(restaurant=restaurant).update(is_active=False)
    MenuSection.objects.filter(restaurant=restaurant).update(is_active=False)

    for raw in items_from_json or []:
        name = (raw.get("name") or "").strip()
        if not name:
            continue

        norm = normalize_name(name)
        if not norm:
            continue

        # relations (these will get re-activated via defaults)
        category_obj = _get_or_create_category(restaurant, raw)
        section_obj = _get_or_create_section(restaurant, category_obj, raw)

        description = raw.get("description") or ""
        price = clean_price(raw.get("price"))
        currency = (raw.get("currency") or "INR").upper()

        ingredients = raw.get("ingredients") or []
        if isinstance(ingredients, str):
            ingredients = [ingredients]

        image_url = raw.get("image_url") or ""

        # POS id (if present)
        external_id = (raw.get("external_item_id") or raw.get("item_id") or "").strip()

        # ✅ generate deterministic id if missing
        if not external_id:
            cat_name = category_obj.name if category_obj else (raw.get("category") or "")
            sec_name = section_obj.name if section_obj else (raw.get("section") or "")
            external_id = _make_llm_item_id(restaurant.id, norm, str(cat_name), str(sec_name))

        raw_blob = raw.get("raw") or raw

        # ✅ Always lookup by (restaurant, external_item_id)
        MenuItem.objects.update_or_create(
            restaurant=restaurant,
            external_item_id=external_id,
            defaults={
                "name": name,
                "normalized_name": norm,
                "description": description,
                "category": category_obj,
                "menu_section": section_obj,
                "price": price,
                "currency": currency,
                "ingredients": ingredients,
                "available": True,
                "is_active": True,  # ✅ reactivate item
                "image_url": image_url,
                "raw_data": raw_blob,
            },
        )
