from django.conf import settings
from django.db import models
import uuid

from customers.models import Customer
from suppliers.models import Supplier
from products.models import Product
from inventory.models import InventoryLocation


class Sale(models.Model):
    PAYMENT_CHOICES = [
        ('cash', 'Cash'),
        ('mobile_money', 'Mobile Money'),
        ('bank_transfer', 'Transfert bancaire'),
        ('credit', 'Crédit'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('paid', 'Payée'),
        ('partial', 'Partielle'),
        ('cancelled', 'Annulée'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='sales')
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='sales_created', null=True, blank=True)
    location = models.ForeignKey(InventoryLocation, on_delete=models.PROTECT, related_name='sales', null=True, blank=True)
    sale_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    payment_method = models.CharField(max_length=30, choices=PAYMENT_CHOICES, default='cash')
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_external = models.BooleanField(default=False)
    external_supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='external_sales', null=True, blank=True)
    external_reference = models.CharField(max_length=120, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-sale_date']

    def __str__(self):
        return f'Vente {self.id} - {self.customer.full_name}'


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='sale_items')
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_price(self):
        return self.quantity * self.unit_price

    class Meta:
        unique_together = ('sale', 'product')

    def __str__(self):
        return f'{self.product.name} x {self.quantity}'


class Invoice(models.Model):
    sale = models.OneToOneField(Sale, on_delete=models.CASCADE, related_name='invoice')
    invoice_number = models.CharField(max_length=80, unique=True)
    verification_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    qr_code = models.CharField(max_length=200, blank=True, default='')
    issue_date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-issue_date']

    def __str__(self):
        return self.invoice_number

    def generate_qr_code(self):
        if self.qr_code:
            return self.qr_code
        self.qr_code = f'NEXORA-INV-{self.invoice_number}-{str(self.verification_token).replace("-", "")[:8].upper()}'
        return self.qr_code

    def save(self, *args, **kwargs):
        if not self.qr_code:
            self.qr_code = self.generate_qr_code()
        super().save(*args, **kwargs)
