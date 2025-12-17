# menu/models.py
from django.db import models
from django.utils.text import slugify

from restaurants.models import Restaurant


# menu/models.py
from django.db import models
from django.db.models import Q
from django.utils.text import slugify
from restaurants.models import Restaurant

class Category(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="categories")
    external_category_id = models.CharField(max_length=50, blank=True, default="", db_index=True)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    position = models.IntegerField(null=True, blank=True)
    raw_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "name"]
        constraints = [
            # ✅ POS id present ho to hi unique enforce
            models.UniqueConstraint(
                fields=["restaurant", "external_category_id"],
                condition=~Q(external_category_id=""),
                name="uniq_category_per_restaurant_external_id",
            ),
            # ✅ LLM/no-id case me restaurant+slug unique
            models.UniqueConstraint(
                fields=["restaurant", "slug"],
                condition=Q(external_category_id=""),
                name="uniq_category_per_restaurant_slug_when_no_external",
            ),
        ]
        indexes = [models.Index(fields=["restaurant", "is_active"])]

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = slugify(self.name)[:255]
        super().save(*args, **kwargs)

class MenuSection(models.Model):
    """
    Optional level between Category and MenuItem.
    In POS JSON: often menu_id / sub_category_data etc.
    In LLM extraction: may not exist (then keep null).
    """
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="menu_sections",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="sections",
    )

    external_menu_id = models.CharField(
        max_length=50,
        blank=True,
        default="",
        db_index=True,
        help_text="External POS section/menu id (if available).",
    )

    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True, db_index=True)
    position = models.IntegerField(null=True, blank=True)

    raw_data = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["category", "external_menu_id"],
                name="uniq_section_per_category_external_id",
            )
        ]
        indexes = [
            models.Index(fields=["restaurant", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.category.name} - {self.restaurant.name}"


class MenuItem(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="menu_items",
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items",
    )
    menu_section = models.ForeignKey(
        MenuSection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items",
    )

    external_item_id = models.CharField(
        max_length=50,
        blank=True,
        default="",
        db_index=True,
        help_text="External POS item id (if available).",
    )

    name = models.CharField(max_length=255)

    normalized_name = models.CharField(
        max_length=255,
        db_index=True,
        blank=True,
        help_text="Lowercased, cleaned name for matching.",
    )

    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    description = models.TextField(blank=True)

    image_url = models.URLField(blank=True)

    available = models.BooleanField(default=True)
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="False means archived (not part of current menu sync).",
    )

    position = models.IntegerField(null=True, blank=True)
    currency = models.CharField(max_length=10, default="INR")

    ingredients = models.JSONField(null=True, blank=True, default=list)

    raw_data = models.JSONField(
        null=True,
        blank=True,
        help_text="Full original item JSON from POS / extractor.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["restaurant", "external_item_id"],
                name="uniq_item_per_restaurant_external_id",
            )
        ]
        indexes = [
            models.Index(fields=["restaurant", "is_active"]),
            models.Index(fields=["restaurant", "available"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.restaurant.name}"


class MenuItemImage(models.Model):
    """
    Optional (only if you need multiple images per item).
    If you don't need this, you can remove this model safely.
    """
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name="images",
    )

    external_attachment_id = models.CharField(max_length=50, blank=True, default="", db_index=True)
    image_url = models.URLField()

    raw_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"Image for {self.menu_item_id}"


