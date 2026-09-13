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
