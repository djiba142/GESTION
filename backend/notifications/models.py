from django.db import models

from sales.models import Sale


class Notification(models.Model):
    CHANNEL_CHOICES = [
        ('whatsapp', 'WhatsApp'),
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('internal', 'Interne'),
    ]

    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('sent', 'Envoyé'),
        ('failed', 'Échec'),
        ('retry', 'Retry'),
    ]

    EVENT_CHOICES = [
        ('sale_confirmed', 'Vente confirmée'),
        ('payment_received', 'Paiement reçu'),
        ('invoice_sent', 'Facture envoyée'),
        ('credit_reminder', 'Rappel crédit'),
    ]

    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    channel = models.CharField(max_length=30, choices=CHANNEL_CHOICES, default='whatsapp')
    event_type = models.CharField(max_length=40, choices=EVENT_CHOICES, default='sale_confirmed')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    message = models.TextField(blank=True, default='')
    recipient_phone = models.CharField(max_length=30, blank=True, default='')
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_event_type_display()} - {self.get_status_display()}'
