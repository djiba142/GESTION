from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from products.models import Product
from inventory.models import StockItem
from core.models import AuditLog
from .models import Invoice, Sale, SaleItem


class SaleItemSerializer(serializers.ModelSerializer):
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = SaleItem
        fields = ['id', 'product', 'quantity', 'unit_price', 'total_price']
        read_only_fields = ['id', 'total_price']

    def get_total_price(self, obj):
        return obj.total_price


class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True)
    total_amount = serializers.SerializerMethodField()
    invoice_number = serializers.SerializerMethodField()
    invoice_qr_code = serializers.SerializerMethodField()
    seller = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.all(), required=False, allow_null=True)

    class Meta:
        model = Sale
        fields = ['id', 'customer', 'seller', 'location', 'sale_date', 'status', 'payment_method', 'total_amount', 'amount_paid', 'is_external', 'external_supplier', 'external_reference', 'notes', 'items', 'invoice_number', 'invoice_qr_code', 'created_at', 'updated_at']
        read_only_fields = ['id', 'sale_date', 'created_at', 'updated_at', 'total_amount', 'invoice_number', 'invoice_qr_code']

    def get_total_amount(self, obj):
        return sum(item.total_price for item in obj.items.all())

    def get_invoice_number(self, obj):
        invoice = getattr(obj, 'invoice', None)
        return invoice.invoice_number if invoice else None

    def get_invoice_qr_code(self, obj):
        invoice = getattr(obj, 'invoice', None)
        return invoice.qr_code if invoice else None

    def validate(self, attrs):
        items = attrs.get('items', [])
        customer = attrs.get('customer')
        if not items:
            raise serializers.ValidationError({'items': 'Une vente doit contenir au moins un article.'})
        if not customer:
            raise serializers.ValidationError({'customer': 'Un client est obligatoire pour enregistrer une vente.'})

        if attrs.get('is_external') and not attrs.get('external_supplier'):
            raise serializers.ValidationError({'external_supplier': 'Le fournisseur est obligatoire pour une vente externe.'})

        total_amount = sum(item['quantity'] * item['unit_price'] for item in items)
        amount_paid = attrs.get('amount_paid', 0) or 0
        if amount_paid < 0 or amount_paid > total_amount:
            raise serializers.ValidationError({'amount_paid': 'Le montant payé doit être compris entre zéro et le total de la vente.'})

        for item_data in items:
            product = item_data.get('product')
            quantity = item_data.get('quantity', 0)
            if product and quantity > product.quantity:
                raise serializers.ValidationError({'quantity': f'Le stock de {product.name} est insuffisant.'})

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        requested_amount_paid = validated_data.get('amount_paid', 0) or 0

        request = self.context.get('request')
        if request and getattr(request, 'user', None) and validated_data.get('seller') is None:
            validated_data['seller'] = request.user

        sale = Sale.objects.create(**validated_data)

        for item_data in items_data:
            product = Product.objects.select_for_update().get(pk=item_data['product'].pk)
            item_data['product'] = product
            item = SaleItem.objects.create(sale=sale, **item_data)
            if sale.location_id:
                stock_item = StockItem.objects.select_for_update().filter(
                    product=product,
                    location_id=sale.location_id,
                ).first()
                if stock_item is None or stock_item.quantity < item.quantity:
                    raise serializers.ValidationError({'quantity': f'Le stock de {product.name} est insuffisant dans cet emplacement.'})
                stock_item.quantity -= item.quantity
                stock_item.save(update_fields=['quantity', 'updated_at'])
            if product.quantity < item.quantity:
                raise serializers.ValidationError({'quantity': f'Le stock de {product.name} est insuffisant.'})
            product.quantity -= item.quantity
            product.save(update_fields=['quantity'])

        sale.total_amount = sum(item.total_price for item in sale.items.all())
        sale.amount_paid = sale.total_amount if sale.status == 'paid' else requested_amount_paid
        sale.save(update_fields=['total_amount', 'amount_paid'])

        invoice_number = f'INV-{sale.id:06d}'
        invoice = Invoice.objects.create(
            sale=sale,
            invoice_number=invoice_number,
            total_amount=sale.total_amount,
            paid_amount=sale.amount_paid,
        )
        invoice.generate_qr_code()
        invoice.save(update_fields=['qr_code'])

        from payments.models import CreditLedger, Payment

        if sale.amount_paid > 0:
            Payment.objects.create(
                customer=sale.customer,
                sale=sale,
                amount=sale.amount_paid,
                payment_method=sale.payment_method,
                reference=f'PAY-SALE-{sale.id:06d}',
                notes='Paiement généré automatiquement lors de la vente',
            )

        if sale.total_amount > sale.amount_paid:
            ledger, _ = CreditLedger.objects.get_or_create(
                customer=sale.customer,
                sale=sale,
                defaults={'total_credit': sale.total_amount, 'total_paid': sale.amount_paid},
            )
            ledger.total_credit = sale.total_amount
            ledger.total_paid = sale.amount_paid
            ledger.update_balance()

        request = self.context.get('request')
        AuditLog.objects.create(
            user=getattr(request, 'user', None) if request else None,
            action='sale',
            model_name='Sale',
            record_id=sale.id,
            details=f'Vente créée: {sale.id}, total={sale.total_amount}',
        )
        return sale
