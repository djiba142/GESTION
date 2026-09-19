from typing import ClassVar

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('sales', 'Sales'),
        ('stock', 'Stock'),
        ('viewer', 'Viewer'),
    ]

    LANGUAGE_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ('fr', 'Français'),
        ('en', 'English'),
    ]
    KEYBOARD_LAYOUT_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ('fr', 'Français'),
        ('us', 'US'),
    ]

    role = models.CharField(max_length=40, choices=ROLE_CHOICES, default='viewer')
    phone = models.CharField(max_length=30, blank=True, default='')
    pin_code = models.CharField(max_length=128, blank=True, default='0000')
    preferred_language = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        default='fr',
    )
    keyboard_layout = models.CharField(
        max_length=10,
        choices=KEYBOARD_LAYOUT_CHOICES,
        default='fr',
    )
    failed_login_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering: ClassVar[list[str]] = ['-created_at']

    def __str__(self):
        full_name = self.get_full_name()
        return full_name or self.username

    @property
    def display_name(self):
        return self.get_full_name() or self.username

    def set_pin(self, raw_pin):
        self.pin_code = make_password(raw_pin)

    def check_pin(self, raw_pin):
        if check_password(raw_pin, self.pin_code):
            return True
        if self.pin_code == raw_pin:
            self.set_pin(raw_pin)
            self.save(update_fields=['pin_code', 'updated_at'])
            return True
        return False
