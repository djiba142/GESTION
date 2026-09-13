from rest_framework import serializers

from sales.models import Invoice


class InvoiceSerializer(serializers.ModelSerializer):
    customer = serializers.SerializerMethodField()
    sale_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id',
            'sale_id',
            'customer',
            'invoice_number',
            'qr_code',
            'issue_date',
            'total_amount',
            'paid_amount',
            'created_at',
        ]
        read_only_fields = ['id', 'invoice_number', 'qr_code', 'issue_date', 'created_at']

    def get_customer(self, obj):
        customer = obj.sale.customer
        return {
            'id': customer.id,
            'full_name': customer.full_name,
            'phone': customer.phone,
        }
