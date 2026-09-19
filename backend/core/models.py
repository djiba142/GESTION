from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Création'),
        ('update', 'Mise à jour'),
        ('delete', 'Suppression'),
        ('login', 'Connexion'),
        ('payment', 'Paiement'),
        ('sale', 'Vente'),
        ('stock', 'Stock'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES, default='create')
    model_name = models.CharField(max_length=120, blank=True, default='')
    record_id = models.PositiveIntegerField(default=0)
    details = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} - {self.action}'


class AppSetting(models.Model):
    key = models.CharField(max_length=120, unique=True)
    value = models.TextField(blank=True, default='')
    description = models.TextField(blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['key']

    def __str__(self):
        return self.key


class Company(models.Model):
    name = models.CharField(max_length=200)
    legal_name = models.CharField(max_length=240, blank=True, default='')
    phone = models.CharField(max_length=30, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    address = models.TextField(blank=True, default='')
    currency = models.CharField(max_length=10, default='GNF')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'companies'

    def __str__(self):
        return self.name


class IdempotencyRecord(models.Model):
    key = models.CharField(max_length=255)
    endpoint = models.CharField(max_length=255)
    scope_hash = models.CharField(max_length=64, unique=True)
    request_hash = models.CharField(max_length=64)
    response_status = models.PositiveSmallIntegerField()
    response_body = models.JSONField(default=dict)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class SyncOperation(models.Model):
    STATUS_CHOICES = [
        ('accepted', 'Acceptée'),
        ('rejected', 'Rejetée'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sync_operations')
    local_id = models.CharField(max_length=120)
    operation_type = models.CharField(max_length=30)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    payload = models.JSONField(default=dict)
    result = models.JSONField(default=dict)
    error = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'local_id'], name='unique_sync_operation_per_user'),
        ]
        ordering = ['-created_at']
