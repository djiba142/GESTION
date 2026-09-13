from decimal import Decimal

from django.db import models

from inventory.models import InventoryLocation, StockItem, StockMovement
from products.models import Product
from suppliers.models import Supplier


class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('submitted', 'Soumise'),
        ('approved', 'Approuvée'),
        ('partial_received', 'Réception partielle'),
        ('received', 'Reçue'),
        ('cancelled', 'Annulée'),
    ]

    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='purchase_orders')
    reference = models.CharField(max_length=120, unique=True)
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='draft')
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_amount(self):
        return sum(item.total_price for item in self.items.all())

    class Meta:
        ordering = ['-order_date']

    def __str__(self):
        return f'{self.reference} - {self.supplier.name}'


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='purchase_order_items')
    quantity = models.IntegerField(default=1)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_price(self):
        return self.quantity * self.unit_cost

    class Meta:
        unique_together = ('purchase_order', 'product')

    def __str__(self):
        return f'{self.product.name} x {self.quantity}'


class PurchaseReceipt(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('partial', 'Partielle'),
        ('received', 'Reçue'),
        ('cancelled', 'Annulée'),
    ]

    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name='receipts')
    reference = models.CharField(max_length=120, unique=True)
    received_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='draft')
    notes = models.TextField(blank=True, default='')
    transport_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    customs_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    handling_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    insurance_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def subtotal(self):
        return sum(item.line_total for item in self.items.all())

    @property
    def total_cost(self):
        return self.subtotal + self.transport_cost + self.customs_cost + self.handling_cost + self.insurance_cost + self.other_cost

    class Meta:
        ordering = ['-received_date']

    def __str__(self):
        return f'{self.reference} - {self.purchase_order.reference}'


class PurchaseReceiptItem(models.Model):
    purchase_receipt = models.ForeignKey(PurchaseReceipt, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='receipt_items')
    quantity_received = models.IntegerField(default=0)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def line_total(self):
        return self.quantity_received * self.unit_cost

    @property
    def acquisition_costs(self):
        if self.quantity_received <= 0:
            return Decimal('0')
        total_acquisition_costs = sum([
            Decimal(str(self.purchase_receipt.transport_cost)),
            Decimal(str(self.purchase_receipt.customs_cost)),
            Decimal(str(self.purchase_receipt.handling_cost)),
            Decimal(str(self.purchase_receipt.insurance_cost)),
            Decimal(str(self.purchase_receipt.other_cost)),
        ])
        return total_acquisition_costs / Decimal(self.quantity_received)

    @property
    def real_unit_cost(self):
        return self.unit_cost + self.acquisition_costs

    @property
    def real_line_total(self):
        return self.quantity_received * self.real_unit_cost

    class Meta:
        unique_together = ('purchase_receipt', 'product')

    def __str__(self):
        return f'{self.product.name} x {self.quantity_received}'
