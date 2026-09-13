from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('sales', 'Sales'),
        ('stock', 'Stock'),
        ('viewer', 'Viewer'),
    ]

    LANGUAGE_CHOICES = [
        ('fr', 'Français'),
        ('en', 'English'),
    ]
    KEYBOARD_LAYOUT_CHOICES = [
        ('fr', 'Français'),
        ('us', 'US'),
    ]

    role = models.CharField(max_length=40, choices=ROLE_CHOICES, default='viewer')
    phone = models.CharField(max_length=30, blank=True, default='')
    pin_code = models.CharField(max_length=6, blank=True, default='0000')
    preferred_language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='fr')
    keyboard_layout = models.CharField(max_length=10, choices=KEYBOARD_LAYOUT_CHOICES, default='fr')
    failed_login_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        full_name = self.get_full_name()
        return full_name or self.username

    @property
    def display_name(self):
        return self.get_full_name() or self.username
