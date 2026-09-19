from rest_framework import serializers

from sales.models import Invoice


def invoice_verification_url(obj):
    from django.conf import settings

    return f'{settings.INVOICE_VERIFICATION_BASE_URL}{obj.verification_token}'


class InvoiceSerializer(serializers.ModelSerializer):
    customer = serializers.SerializerMethodField()
    sale_id = serializers.IntegerField(read_only=True)
    verification_url = serializers.SerializerMethodField()
    qr_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            'id',
            'sale_id',
            'customer',
            'invoice_number',
            'qr_code',
            'verification_url',
            'qr_image_url',
            'issue_date',
            'total_amount',
            'paid_amount',
            'created_at',
        ]
        read_only_fields = ['id', 'invoice_number', 'qr_code', 'verification_token', 'verification_url', 'qr_image_url', 'issue_date', 'created_at']

    def get_customer(self, obj):
        customer = obj.sale.customer
        return {
            'id': customer.id,
            'full_name': customer.full_name,
            'phone': customer.phone,
        }

    def get_verification_url(self, obj):
        return invoice_verification_url(obj)

    def get_qr_image_url(self, obj):
        request = self.context.get('request')
        path = f'/api/invoices/{obj.pk}/qr-image/'
        return request.build_absolute_uri(path) if request else path
