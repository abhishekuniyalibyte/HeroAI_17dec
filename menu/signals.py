# menu/signals.py
from threading import local

from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import MenuItem
from .tasks import regenerate_menu_embeddings_for_restaurant
from .embedding_context import are_embedding_signals_disabled

_thread_local = local()


def _get_pending_restaurant_ids():
    if not hasattr(_thread_local, "pending_restaurant_ids"):
        _thread_local.pending_restaurant_ids = set()
    return _thread_local.pending_restaurant_ids


def _schedule_regeneration_for_restaurant(restaurant_id: int | None) -> None:
    if not restaurant_id:
        return

    if are_embedding_signals_disabled():
        return

    pending_ids = _get_pending_restaurant_ids()
    pending_ids.add(restaurant_id)

    if getattr(_thread_local, "on_commit_registered", False):
        return

    _thread_local.on_commit_registered = True

    def _on_commit():
        ids = _get_pending_restaurant_ids().copy()
        pending_ids.clear()
        _thread_local.on_commit_registered = False

        for rid in ids:
            regenerate_menu_embeddings_for_restaurant.delay(rid)

    transaction.on_commit(_on_commit)


@receiver(post_save, sender=MenuItem)
def menuitem_saved(sender, instance: MenuItem, created, **kwargs):
    _schedule_regeneration_for_restaurant(instance.restaurant_id)


@receiver(post_delete, sender=MenuItem)
def menuitem_deleted(sender, instance: MenuItem, **kwargs):
    _schedule_regeneration_for_restaurant(instance.restaurant_id)
