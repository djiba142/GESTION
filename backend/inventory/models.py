from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class InventoryLocation(models.Model):
    LOCATION_TYPES = [
        ('warehouse', 'Warehouse'),
        ('shop', 'Shop'),
        ('storage', 'Storage'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=80, unique=True)
    location_type = models.CharField(max_length=40, choices=LOCATION_TYPES, default='warehouse')
    address = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.code})'


class StockItem(models.Model):
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='stock_items')
    location = models.ForeignKey(InventoryLocation, on_delete=models.CASCADE, related_name='stock_items')
    quantity = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'location')
        ordering = ['product__name', 'location__name']

    def __str__(self):
        return f'{self.product.name} @ {self.location.name}: {self.quantity}'

    def add_quantity(self, value):
        self.quantity = max(0, self.quantity + value)
        self.save(update_fields=['quantity', 'updated_at'])

    def remove_quantity(self, value):
        if self.quantity - value < 0:
            raise ValidationError('La quantité en stock ne peut pas devenir négative.')
        self.quantity -= value
        self.save(update_fields=['quantity', 'updated_at'])


class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ('in', 'Entrée'),
        ('out', 'Sortie'),
        ('adjustment', 'Ajustement'),
    ]

    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='stock_movements')
    location = models.ForeignKey(InventoryLocation, on_delete=models.CASCADE, related_name='stock_movements')
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.IntegerField(default=0)
    reference = models.CharField(max_length=120, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_movements')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_movement_type_display()} - {self.product.name} ({self.quantity})'


class StockTransfer(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('requested', 'Demandé'),
        ('validated', 'Validé'),
        ('shipped', 'Expédié'),
        ('received', 'Reçu'),
        ('cancelled', 'Annulé'),
    ]

    product = models.ForeignKey('products.Product', on_delete=models.PROTECT, related_name='stock_transfers')
    from_location = models.ForeignKey(InventoryLocation, on_delete=models.PROTECT, related_name='outgoing_transfers')
    to_location = models.ForeignKey(InventoryLocation, on_delete=models.PROTECT, related_name='incoming_transfers')
    quantity = models.PositiveIntegerField(default=0)
    reference = models.CharField(max_length=120, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='validated')
    notes = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_transfers')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.reference} - {self.product.name}'

    def clean(self):
        if self.from_location_id == self.to_location_id:
            raise ValidationError('La source et la destination d’un transfert doivent être différentes.')
        if self.quantity <= 0:
            raise ValidationError('La quantité du transfert doit être positive.')
        source_item = StockItem.objects.filter(product=self.product, location=self.from_location).first()
        if source_item and source_item.quantity < self.quantity:
            raise ValidationError('La quantité demandée dépasse le stock disponible dans l’emplacement source.')

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Carton(models.Model):
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT, related_name='cartons')
    location = models.ForeignKey(InventoryLocation, on_delete=models.PROTECT, related_name='cartons')
    reference = models.CharField(max_length=120, unique=True)
    quantity = models.PositiveIntegerField(default=0)
    items_per_carton = models.PositiveIntegerField(default=1)
    qr_code = models.CharField(max_length=200, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.reference} - {self.product.name}'

    def generate_qr_code(self):
        if self.qr_code:
            return self.qr_code
        self.qr_code = f'NEXORA-CTN-{self.reference or self.pk or "NEW"}'
        return self.qr_code

    def save(self, *args, **kwargs):
        if not self.qr_code:
            self.qr_code = self.generate_qr_code()
        super().save(*args, **kwargs)
