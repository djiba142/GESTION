from django.db import models
from django.utils import timezone


class Supplier(models.Model):
    name = models.CharField(max_length=200)
    contact_name = models.CharField(max_length=200, blank=True, default='')
    phone = models.CharField(max_length=30, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    address = models.TextField(blank=True, default='')
    company_name = models.CharField(max_length=200, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class ExchangeRate(models.Model):
    source_currency = models.CharField(max_length=10, default='USD')
    target_currency = models.CharField(max_length=10, default='GNF')
    rate = models.DecimalField(max_digits=18, decimal_places=6, default=1)
    effective_date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-effective_date', '-created_at']
        unique_together = ('source_currency', 'target_currency', 'effective_date')

    def __str__(self):
        return f'{self.source_currency} -> {self.target_currency} : {self.rate}'


class SupplierImport(models.Model):
    STATUS_CHOICES = [
        ('parsed', 'Traité'),
        ('validated', 'Validé'),
        ('rejected', 'Rejeté'),
    ]

    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='supplier_imports')
    purchase_order = models.ForeignKey(
        'purchases.PurchaseOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supplier_imports',
    )
    file_name = models.CharField(max_length=255, blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='parsed')
    parsed_rows = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.file_name or "Import fournisseur"} - {self.supplier.name}'


class SupplierImportRow(models.Model):
    supplier_import = models.ForeignKey(SupplierImport, on_delete=models.CASCADE, related_name='rows')
    reference = models.CharField(max_length=120, blank=True, default='')
    name = models.CharField(max_length=220, blank=True, default='')
    quantity = models.PositiveIntegerField(default=0)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default='USD')
    matched_product = models.CharField(max_length=200, blank=True, default='')
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.reference or self.name} - {self.quantity}'

