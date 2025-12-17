# chatbot/models.py
import secrets
from django.conf import settings
from django.db import models

from restaurants.models import Restaurant


class RestaurantWidget(models.Model):
    restaurant = models.OneToOneField(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="widget",
    )
    public_token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Public token for iframe embed URL.",
    )
    is_active = models.BooleanField(default=True)
    allowed_domains = models.TextField(
        blank=True,
        help_text="Optional: comma-separated list of allowed domains for embedding.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Agar token nahi hai to generate kar do
        if not self.public_token:
            self.public_token = secrets.token_urlsafe(16)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Widget for {self.restaurant.name}"

    @property
    def iframe_src(self) -> str:
        """
        Full iframe src URL for this widget.
        e.g. http://127.0.0.1:8000/api/chatbot/widget/?token=...
        """
        base = getattr(settings, "PUBLIC_BASE_URL", "").rstrip("/")
        return f"{base}/api/chatbot/widget/?token={self.public_token}"
