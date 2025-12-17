# accounts/permission_config.py

PERMISSION_CONFIG = {
    "superadmin": {
        # special: give all permissions
        "__all__": ["*"],
    },
    "admin": {
        # Only allow what an admin should do.
        # Adjust this list for your project structure.

        # Can view restaurants (but row-level scoping we handle in ModelAdmin/get_queryset)
        "restaurants.Restaurant": ["view"],

        # Can manage their own menu items
        "menu.MenuItem": ["view", "add", "change"],
        "orders.Order" : ["view", "add", "change"]
    },
}
