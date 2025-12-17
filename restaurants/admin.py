from django.contrib import admin, messages
from django import forms
from django.forms.widgets import ClearableFileInput
from django.urls import path
from django.shortcuts import redirect

from .models import (
    Restaurant,
    RestaurantMenuImage,
    RestaurantMenuPDF,
)

# If you added MenuImportJob in restaurants/models.py, import it too.
# If you haven't added it yet, keep this import commented.
try:
    from .models import MenuImportJob
except Exception:
    MenuImportJob = None

from .tasks import extract_menu_for_restaurant_task  # Celery task


# -------------------------------------------------
# 1) Multi-file widget + field (admin ke liye)
# -------------------------------------------------

class MultiFileInput(ClearableFileInput):
    """ <input type="file" multiple> """
    allow_multiple_selected = True


class MultiFileField(forms.FileField):
    """ FileField → hamesha list of files return karega """
    widget = MultiFileInput

    def clean(self, data, initial=None):
        if not data:
            return []
        if not isinstance(data, (list, tuple)):
            data = [data]
        cleaned_files = []
        for f in data:
            cleaned_files.append(super().clean(f, initial))
        return cleaned_files


# -------------------------------------------------
# 2) Restaurant custom admin form
# -------------------------------------------------

class RestaurantAdminForm(forms.ModelForm):
    new_images = MultiFileField(
        required=False,
        label="Upload new menu images",
        help_text="Ctrl/Shift daba ke ek hi baar multiple images select kar sakte ho.",
    )

    new_pdfs = MultiFileField(
        required=False,
        label="Upload new menu PDFs",
        help_text="Ctrl/Shift daba ke ek hi baar multiple PDFs select kar sakte ho.",
    )

    # Optional checkbox: Save ke baad extraction bhi chalani ho to isko tick karo
    run_extraction = forms.BooleanField(
        required=False,
        label="Run menu extraction after saving",
        help_text="Tick karoge to save ke baad menu extraction background me Celery se chalegi.",
    )

    class Meta:
        model = Restaurant
        fields = "__all__"


# -------------------------------------------------
# 3) Inline to show existing menu images / pdfs
# -------------------------------------------------

class RestaurantMenuImageInline(admin.TabularInline):
    model = RestaurantMenuImage
    extra = 0
    fields = ["image", "sort_order", "uploaded_at"]
    readonly_fields = ["uploaded_at"]


class RestaurantMenuPDFInline(admin.TabularInline):
    model = RestaurantMenuPDF
    extra = 0
    fields = ["pdf", "uploaded_at"]
    readonly_fields = ["uploaded_at"]


@admin.register(RestaurantMenuImage)
class RestaurantMenuImageAdmin(admin.ModelAdmin):
    list_display = ("id", "restaurant", "sort_order", "uploaded_at")
    list_filter = ("restaurant",)
    search_fields = ("restaurant__name",)
    readonly_fields = ("uploaded_at",)


@admin.register(RestaurantMenuPDF)
class RestaurantMenuPDFAdmin(admin.ModelAdmin):
    list_display = ("id", "restaurant", "uploaded_at")
    list_filter = ("restaurant",)
    search_fields = ("restaurant__name",)
    readonly_fields = ("uploaded_at",)


# -------------------------------------------------
# 4) Optional: MenuImportJob admin (if you created it)
# -------------------------------------------------

if MenuImportJob is not None:

    @admin.register(MenuImportJob)
    class MenuImportJobAdmin(admin.ModelAdmin):
        list_display = (
            "id",
            "restaurant",
            "status",
            "progress",
            "created_at",
            "started_at",
            "finished_at",
        )
        list_filter = ("status", "restaurant")
        search_fields = ("restaurant__name",)
        readonly_fields = (
            "status",
            "progress",
            "error_message",
            "started_at",
            "finished_at",
            "created_at",
        )


# -------------------------------------------------
# 5) MAIN: RestaurantAdmin
# -------------------------------------------------

@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    form = RestaurantAdminForm
    inlines = [RestaurantMenuImageInline, RestaurantMenuPDFInline]

    list_display = (
        "id",
        "name",
        "phone",
        "is_active",
        "menu_extract_status",
        "pos_source",
        "pos_store_id",
        "pos_menu_last_synced_at",
        "created_at",
    )
    list_filter = ("is_active", "menu_extract_status", "pos_source")
    search_fields = ("name", "phone", "pos_store_id")
    readonly_fields = (
        "created_at",
        "updated_at",
        "menu_last_extracted_at",
        "pos_menu_last_synced_at",
    )

    # Custom template for "Extract Now" button
    change_form_template = "admin/restaurants/restaurant/change_form.html"

    # ---------------------------
    # PERMISSION LOGIC
    # ---------------------------
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user = request.user

        if user.is_superuser or getattr(user, "is_superadmin", False):
            return qs

        if getattr(user, "is_restaurant_admin", False):
            # Your Restaurant model has owner = OneToOneField(User)
            return qs.filter(owner=user)

        return qs.none()

    def has_view_permission(self, request, obj=None):
        user = request.user
        if user.is_superuser or getattr(user, "is_superadmin", False):
            return True
        if not getattr(user, "is_restaurant_admin", False):
            return False
        if obj is None:
            return True
        return obj.owner_id == user.id

    def has_change_permission(self, request, obj=None):
        user = request.user
        if user.is_superuser or getattr(user, "is_superadmin", False):
            return True
        if not getattr(user, "is_restaurant_admin", False):
            return False
        if obj is None:
            return True
        return obj.owner_id == user.id

    def has_add_permission(self, request):
        user = request.user
        return user.is_superuser or getattr(user, "is_superadmin", False)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    # -------------------------------------------------
    # save_model: Restaurant + images/pdfs + optional extraction
    # -------------------------------------------------
    def save_model(self, request, obj, form, change):
        """
        Save restaurant + handle image/PDF uploads (delete ALL old assets + save new)
        and optionally run extraction (Celery background task).
        """
        super().save_model(request, obj, form, change)

        files = form.cleaned_data.get("new_images") or []
        pdf_files = form.cleaned_data.get("new_pdfs") or []

        # If any new assets uploaded: wipe old batch then save new batch
        if files or pdf_files:
            # old images
            for img in obj.menu_images.all():
                if img.image:
                    img.image.delete(save=False)
                img.delete()

            # old pdfs
            for pdf in obj.menu_pdfs.all():
                if pdf.pdf:
                    pdf.pdf.delete(save=False)
                pdf.delete()

            # new images
            for idx, f in enumerate(files):
                RestaurantMenuImage.objects.create(
                    restaurant=obj,
                    image=f,
                    sort_order=idx,
                )

            # new pdfs
            for f in pdf_files:
                RestaurantMenuPDF.objects.create(
                    restaurant=obj,
                    pdf=f,
                )

        # optional extraction
        if form.cleaned_data.get("run_extraction"):
            self._run_extraction_for_restaurant(request, obj)

    # -------------------------------------------------
    # Celery-based extraction trigger
    # -------------------------------------------------
    def _run_extraction_for_restaurant(self, request, restaurant):
        try:
            extract_menu_for_restaurant_task.delay(restaurant.id)
        except Exception as e:
            messages.error(request, f"❌ Menu extraction task start nahi ho paya: {e}")
            return False

        messages.success(
            request,
            "✅ Menu extraction background me start ho chuki hai. "
            "Thodi der baad MenuItems aur JSON update ho jayenge."
        )
        return True

    # -------------------------------------------------
    # CUSTOM URL → /extract/ (button ke liye)
    # -------------------------------------------------
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:restaurant_id>/extract/",
                self.admin_site.admin_view(self.extract_menu_now),
                name="restaurant_extract_now",
            )
        ]
        return custom + urls

    def extract_menu_now(self, request, restaurant_id):
        try:
            restaurant = Restaurant.objects.get(id=restaurant_id)
        except Restaurant.DoesNotExist:
            messages.error(request, "Restaurant not found.")
            return redirect("../../")

        self._run_extraction_for_restaurant(request, restaurant)
        return redirect("../")
