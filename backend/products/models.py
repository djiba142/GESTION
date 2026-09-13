from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    sku = models.CharField(max_length=80, unique=True)
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    brand = models.CharField(max_length=120, blank=True, default='')
    description = models.TextField(blank=True, default='')
    unit = models.CharField(max_length=60, default='piece')
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default='GNF')
    quantity = models.IntegerField(default=0)
    alert_threshold = models.IntegerField(default=0)
    barcode = models.CharField(max_length=120, blank=True, default='')
    qr_code = models.CharField(max_length=200, blank=True, default='')
    image = models.URLField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.sku})'

    def generate_qr_code(self):
        if self.qr_code:
            return self.qr_code

        identifier = self.sku or f'PRD-{self.pk or 0:06d}'
        self.qr_code = f'NEXORA-{identifier}'
        return self.qr_code

    def save(self, *args, **kwargs):
        if not self.qr_code:
            self.qr_code = self.generate_qr_code()
        super().save(*args, **kwargs)
