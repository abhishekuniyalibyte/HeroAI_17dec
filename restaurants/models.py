# restaurants/models.py
from django.db import models
from accounts.models import User

MENU_STATUS_CHOICES = [
    ("idle", "Idle"),
    ("pending", "Pending"),
    ("processing", "Processing"),
    ("succeeded", "Succeeded"),
    ("failed", "Failed"),
]


class Restaurant(models.Model):
    owner = models.OneToOneField(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_restaurants",
    )

    name = models.CharField(max_length=255)
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20)
    logo = models.ImageField(upload_to="restaurant_logos/", null=True, blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ---------- LLM extractor output ----------
    menu_json = models.FileField(
        upload_to="restaurant_menus/json/",
        null=True,
        blank=True,
        help_text="LLM-based extracted menu JSON file (from images/PDFs).",
    )

    menu_extract_status = models.CharField(
        max_length=12,
        choices=MENU_STATUS_CHOICES,
        default="idle",
    )

    menu_last_extracted_at = models.DateTimeField(null=True, blank=True)

    menu_extract_error = models.TextField(
        blank=True,
        default="",
        help_text="Error message if extraction fails",
    )

    # ---------- External POS dump ----------
    pos_source = models.CharField(max_length=50, blank=True)
    pos_store_id = models.CharField(max_length=100, blank=True)

    pos_menu_raw = models.JSONField(
        null=True,
        blank=True,
        help_text="Latest raw menu JSON as received from external POS (full dump).",
    )

    pos_menu_last_synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_menu_sources_for_ai(self):
        return {
            "images": [img.image.path for img in self.menu_images.all()],
            "pdfs": [pdf.pdf.path for pdf in self.menu_pdfs.all()],
        }

    def has_any_menu_assets(self):
        return self.menu_images.exists() or self.menu_pdfs.exists()


class RestaurantMenuImage(models.Model):
    restaurant = models.ForeignKey(
        Restaurant, on_delete=models.CASCADE, related_name="menu_images"
    )
    image = models.ImageField(upload_to="restaurant_menus/images/")
    sort_order = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.restaurant.name} — image {self.id}"


class RestaurantMenuPDF(models.Model):
    restaurant = models.ForeignKey(
        Restaurant, on_delete=models.CASCADE, related_name="menu_pdfs"
    )
    pdf = models.FileField(upload_to="restaurant_menus/pdfs/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.restaurant.name} — pdf {self.id}"


class MenuImportJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RUNNING = "RUNNING", "Running"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="menu_import_jobs",
    )

    source_file = models.FileField(upload_to="restaurant_menus/pos_json/")
    source_json = models.JSONField(null=True, blank=True)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    progress = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, default="")

    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
