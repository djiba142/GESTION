from rest_framework import serializers

from .models import ExchangeRate, Supplier, SupplierImport, SupplierImportRow


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

    class Meta:
        model = SupplierImport
        fields = ['id', 'supplier', 'file_name', 'status', 'parsed_rows', 'created_at', 'rows']
        read_only_fields = ['id', 'created_at', 'rows']
