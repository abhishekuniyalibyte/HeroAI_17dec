# restaurants/menu_utils.py

import os
import tempfile
import requests

from .menu_extractor import (
    convert_pdf_to_images_in_memory,
    extract_restaurant_info,
    extract_menu_to_json,
    GROQ_API_KEY,
)


def extract_menu_from_path(path, groq_api_key=None):
    """Local path (PDF / image) se menu JSON nikaalna using hero-ai pipeline.

    Returns combined structure:

    {
      "restaurant_name": str | None,
      "phone": str | None,
      "categories": [
        {
          "category": "string",
          "items": [{"name": "string", "price": number}]
        },
        ...
      ]
    }
    """
    if groq_api_key is None:
        groq_api_key = GROQ_API_KEY

    path = str(path)

    if not os.path.exists(path):
        raise FileNotFoundError(f"Menu file not found: {path}")

    # 1) bytes list banao (PDF → multiple pages, image → single page)
    if path.lower().endswith(".pdf"):
        image_bytes_list = convert_pdf_to_images_in_memory(path)
        if not image_bytes_list:
            return None
    else:
        with open(path, "rb") as f:
            image_bytes_list = [f.read()]

    if not image_bytes_list:
        return None

    # 2) first page se restaurant info
    try:
        restaurant_info = extract_restaurant_info(image_bytes_list[0], groq_api_key)
    except Exception:
        restaurant_info = {"restaurant_name": None, "phone": None}

    # 3) har page se categories collect karo
    all_categories = []
    for idx, img_bytes in enumerate(image_bytes_list, start=1):
        print(f"[menu-utils] extracting page {idx}/{len(image_bytes_list)} from {path}")
        page_data = extract_menu_to_json(img_bytes, groq_api_key)
        if not page_data:
            print(f"[menu-utils] ✗ Failed to extract page {idx}")
            continue

        cats = page_data.get("categories") or []
        all_categories.extend(cats)
        print(f"[menu-utils] ✓ Extracted {len(cats)} categories from page {idx}")

    if not all_categories and not restaurant_info:
        return None

    combined = {
        "restaurant_name": (restaurant_info or {}).get("restaurant_name"),
        "phone": (restaurant_info or {}).get("phone"),
        "categories": all_categories,
    }
    return combined


def extract_menu_from_url(url, groq_api_key=None):
    """URL se image/PDF download karo, temp file banao,
    aur extract_menu_from_path(...) se process karo.
    """
    if groq_api_key is None:
        groq_api_key = GROQ_API_KEY

    tmp_path = None
    try:
        resp = requests.get(url, stream=True, timeout=30)
        resp.raise_for_status()

        # temp file banate hain same extension ke saath (agar mil jaaye)
        ext = os.path.splitext(url.split("?")[0])[1] or ".bin"
        fd, tmp_path = tempfile.mkstemp(suffix=ext)
        os.close(fd)

        with open(tmp_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return extract_menu_from_path(tmp_path, groq_api_key)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
