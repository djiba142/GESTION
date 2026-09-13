from django.db.models import Sum
from rest_framework import serializers

from core.models import AuditLog
from .models import CreditLedger, Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'customer', 'sale', 'amount', 'payment_method', 'reference', 'payment_date', 'notes']
        read_only_fields = ['id', 'payment_date']

    def create(self, validated_data):
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None

        amount = validated_data.get('amount', 0)
        if amount <= 0:
            raise serializers.ValidationError({'amount': 'Le montant du paiement doit être strictement positif.'})

        sale = validated_data.get('sale')
        if sale:
            paid_before = sale.payments.aggregate(total=Sum('amount'))['total'] or 0
            if paid_before + amount > sale.total_amount:
                raise serializers.ValidationError({'amount': 'Le paiement dépasse le solde restant de la vente.'})

        payment = Payment.objects.create(**validated_data)

        if sale:
            paid_total = sale.payments.aggregate(total=Sum('amount'))['total'] or 0
            sale.amount_paid = paid_total
            sale.status = 'paid' if paid_total >= sale.total_amount else 'partial'
            sale.save(update_fields=['amount_paid', 'status', 'updated_at'])
            if hasattr(sale, 'invoice'):
                sale.invoice.paid_amount = paid_total
                sale.invoice.save(update_fields=['paid_amount'])
            ledger, _ = CreditLedger.objects.get_or_create(
                customer=sale.customer,
                sale=sale,
                defaults={'total_credit': sale.total_amount},
            )
            ledger.total_credit = sale.total_amount
            ledger.total_paid = paid_total
            ledger.update_balance()

        AuditLog.objects.create(
            user=user,
            action='payment',
            model_name='Payment',
            record_id=payment.id,
            details=(
                f"Paiement enregistré : {payment.amount} "
                f"pour la vente {payment.sale_id or 'non associée'} "
                f"via {payment.get_payment_method_display()}"
            ),
        )
        return payment


class CreditLedgerSerializer(serializers.ModelSerializer):
    remaining_balance = serializers.SerializerMethodField()

    class Meta:
        model = CreditLedger
        fields = ['id', 'customer', 'sale', 'total_credit', 'total_paid', 'balance', 'remaining_balance', 'updated_at']
        read_only_fields = ['id', 'balance', 'remaining_balance', 'updated_at']

    def get_remaining_balance(self, obj):
        return obj.remaining_balance
