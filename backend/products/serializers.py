from rest_framework import serializers

from .models import Category, Product


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()
    margin_amount = serializers.SerializerMethodField()
    margin_percent = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'sku', 'name', 'category', 'category_name', 'brand', 'description',
            'unit', 'purchase_price', 'cost_price', 'selling_price', 'currency', 'quantity',
            'alert_threshold', 'barcode', 'qr_code', 'image', 'is_active',
            'created_at', 'updated_at', 'margin_amount', 'margin_percent'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'margin_amount', 'margin_percent']

    def get_category_name(self, obj):
        return obj.category.name if obj.category else None

    def get_margin_amount(self, obj):
        return obj.selling_price - obj.cost_price

    def get_margin_percent(self, obj):
        if not obj.cost_price:
            return 0
        return round(float((obj.selling_price - obj.cost_price) / obj.cost_price * 100), 2)
