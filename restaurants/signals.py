# # restaurants/signals.py
# from django.db.models.signals import pre_save, post_save
# from django.dispatch import receiver
# from django.db import transaction
# from django.conf import settings
# import os

# from .models import Restaurant
# from restaurants.menu_extractor import MenuExtractor
# from myapp import build_menu_from_json  # << new import
# from .tasks import extract_menu_for_restaurant



# @receiver(pre_save, sender=Restaurant)
# def _flag_pdf_change(sender, instance: Restaurant, **kwargs):
#     """
#     Set a flag on the instance if menu_pdf has actually changed.
#     So we don't re-run extraction on every save.
#     """
#     if not instance.pk:
#         # New restaurant
#         instance._menu_pdf_changed = bool(instance.menu_pdf)
#         return

#     try:
#         old = sender.objects.get(pk=instance.pk)
#     except sender.DoesNotExist:
#         instance._menu_pdf_changed = bool(instance.menu_pdf)
#         return

#     old_name = old.menu_pdf.name or ""
#     new_name = instance.menu_pdf.name or ""
#     instance._menu_pdf_changed = (old_name != new_name) and bool(new_name)

# @receiver(post_save, sender=Restaurant)
# def _process_pdf_after_save(sender, instance: Restaurant, **kwargs):
#     """
#     After Restaurant is saved,
#     if menu_pdf changed, run extractor and rebuild MenuItems.
#     """

#     if not getattr(instance, "_menu_pdf_changed", False):
#         return  # no change in PDF, nothing to do

#     def _go():
#         # This runs only after DB commit
#         if not instance.menu_pdf:
#             return

#         pdf_path = instance.menu_pdf.path  # absolute path
#         extractor = MenuExtractor()

#         # 1) extract list[MenuItem] from PDF
#         items = extractor.extract(pdf_path)

#         # 2) save JSON next to the PDF
#         output_dir = os.path.dirname(pdf_path)
#         json_filename = f"menu_structured_{instance.id}.json"
#         output_path = os.path.join(output_dir, json_filename)

#         extractor.save_json(items, output_path)

#         # 3) build MenuItem rows from JSON
#         build_menu_from_json(json_filename=output_path, restaurant=instance)

#         print(f"[signals] Menu rebuilt for restaurant {instance.id}")

#     # ensure this runs only after transaction commit
#     transaction.on_commit(_go)