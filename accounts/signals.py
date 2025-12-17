from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver

from .permission_config import PERMISSION_CONFIG

User = get_user_model()


@receiver(post_migrate)
def setup_role_groups(sender, **kwargs):
    """
    After migrations, ensure Groups and their Permissions match PERMISSION_CONFIG.
    Runs for all apps; we guard with PERMISSION_CONFIG.
    """
    # Avoid running before auth/permissions exist
    if "auth" not in sender.name and "accounts" not in sender.name:
        # still okay; this will be called multiple times, harmless
        pass

    with transaction.atomic():
        for role, model_map in PERMISSION_CONFIG.items():
            group_name = role.capitalize()  # "superadmin" -> "Superadmin" (or choose your style)
            group, _ = Group.objects.get_or_create(name=group_name)

            # If this role has "__all__: ['*']", give all perms
            if "__all__" in model_map and "*" in model_map["__all__"]:
                group.permissions.set(Permission.objects.all())
                continue

            perms_to_assign = []

            for model_path, actions in model_map.items():
                if model_path == "__all__":
                    continue

                app_label, model_name = model_path.split(".")
                model_name = model_name.lower()  # ContentType uses lowercase model name

                try:
                    ct = ContentType.objects.get_by_natural_key(app_label, model_name)
                except ContentType.DoesNotExist:
                    continue  # model might not exist yet

                for action in actions:
                    codename = f"{action}_{model_name}"  # e.g. "view_menuitem"
                    try:
                        perm = Permission.objects.get(content_type=ct, codename=codename)
                        perms_to_assign.append(perm)
                    except Permission.DoesNotExist:
                        # ignore if not created (e.g. typo or model missing)
                        pass

            group.permissions.set(perms_to_assign)


@receiver(post_save, sender=User)
def assign_role_group(sender, instance, **kwargs):
    """
    Whenever a User is created/updated, sync their role -> correct Group.
    """
    role = getattr(instance, "role", None)
    if not role or role not in PERMISSION_CONFIG:
        return

    target_group_name = role.capitalize()
    role_group_names = [r.capitalize() for r in PERMISSION_CONFIG.keys()]

    # Remove from all role-based groups except the target
    instance.groups.remove(
        *Group.objects.filter(name__in=role_group_names).exclude(name=target_group_name)
    )

    # Ensure target group exists & add
    group, _ = Group.objects.get_or_create(name=target_group_name)
    instance.groups.add(group)
