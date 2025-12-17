# accounts/models.py
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

class UserManager(BaseUserManager):
    def create_user(self, username, email=None, password=None, **extra_fields):
        if not username:
            raise ValueError("The username must be set")

        email = self.normalize_email(email)

        # Default: normal admin-type user (can log into admin if you want)
        extra_fields.setdefault("role", "admin")
        extra_fields.setdefault("is_staff", True)       # can access admin UI
        extra_fields.setdefault("is_superuser", False)  # NOT superuser

        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        # Superadmin = full power
        extra_fields.setdefault("role", "superadmin")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(username, email, password, **extra_fields)

class User(AbstractUser):
    ROLE_CHOICES = (
        ("superadmin", "Super Admin"),
        ("admin", "Admin"),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="admin")

    objects = UserManager()  # <-- IMPORTANT

    

    @property
    def is_superadmin(self):
        # play nice with Django’s builtin superuser flag
        return self.is_superuser or self.role == "superadmin"

    @property
    def is_restaurant_admin(self):
        return self.role == "admin"
    
    def save(self, *args, **kwargs):
        # enforce invariants based on role
        if self.role == "admin":
            self.is_staff = True

        if self.role == "superadmin":
            self.is_staff = True
            # if you want every superadmin to truly be a Django superuser:
            self.is_superuser = True

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

