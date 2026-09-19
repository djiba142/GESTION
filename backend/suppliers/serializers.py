from rest_framework import serializers

from purchases.serializers import PurchaseOrderSerializer
from .models import ExchangeRate, Supplier, SupplierImport, SupplierImportRow


class SupplierImportRequestSerializer(serializers.Serializer):
    supplier = serializers.IntegerField()
    file = serializers.FileField()


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'contact_name', 'phone', 'email', 'address',
            'company_name', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ExchangeRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExchangeRate
        fields = ['id', 'source_currency', 'target_currency', 'rate', 'effective_date', 'created_at']
        read_only_fields = ['id', 'created_at']


class SupplierImportRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierImportRow
        fields = ['id', 'reference', 'name', 'quantity', 'unit_price', 'currency', 'matched_product', 'notes']
        read_only_fields = ['id']


class SupplierImportSerializer(serializers.ModelSerializer):
    rows = SupplierImportRowSerializer(many=True, read_only=True)
    purchase_order = serializers.SerializerMethodField()

    class Meta:
        model = SupplierImport
        fields = ['id', 'supplier', 'file_name', 'status', 'parsed_rows', 'created_at', 'rows', 'purchase_order']
        read_only_fields = ['id', 'created_at', 'rows', 'purchase_order']

    def get_purchase_order(self, obj):
        if not getattr(obj, 'purchase_order', None):
            return None
        return PurchaseOrderSerializer(obj.purchase_order).data
