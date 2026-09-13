from decimal import Decimal

from django.db import models

from customers.models import Customer
from sales.models import Sale


class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('mobile_money', 'Mobile Money'),
        ('bank_transfer', 'Transfert bancaire'),
        ('credit', 'Crédit'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='payments')
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name='payments', null=True, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES, default='cash')
    reference = models.CharField(max_length=120, unique=True, blank=True, default='')
    payment_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-payment_date']

    def __str__(self):
        return f'{self.reference or self.id} - {self.amount}'


class CreditLedger(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='credit_ledgers')
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='credit_ledgers', null=True, blank=True)
    total_credit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_paid = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('customer', 'sale')

    @property
    def remaining_balance(self):
        return self.total_credit - self.total_paid

    def update_balance(self):
        self.balance = self.total_credit - self.total_paid
        self.save(update_fields=['total_credit', 'total_paid', 'balance', 'updated_at'])
