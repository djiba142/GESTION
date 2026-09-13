from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from inventory.models import InventoryLocation, StockItem, StockMovement
from .models import PurchaseOrder, PurchaseOrderItem, PurchaseReceipt, PurchaseReceiptItem


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrderItem
        fields = ['id', 'product', 'quantity', 'unit_cost', 'total_price']
        read_only_fields = ['id', 'total_price']

    def get_total_price(self, obj):
        return obj.total_price


class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True)
    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrder
        fields = ['id', 'supplier', 'reference', 'order_date', 'status', 'notes', 'total_amount', 'items', 'created_at', 'updated_at']
        read_only_fields = ['id', 'order_date', 'created_at', 'updated_at', 'total_amount']

    def get_total_amount(self, obj):
        return obj.total_amount

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        purchase_order = PurchaseOrder.objects.create(**validated_data)
        for item_data in items_data:
            PurchaseOrderItem.objects.create(purchase_order=purchase_order, **item_data)
        return purchase_order

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                PurchaseOrderItem.objects.create(purchase_order=instance, **item_data)
        return instance


class PurchaseReceiptItemSerializer(serializers.ModelSerializer):
    line_total = serializers.SerializerMethodField()
    real_unit_cost = serializers.SerializerMethodField()
    real_line_total = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseReceiptItem
        fields = ['id', 'product', 'quantity_received', 'unit_cost', 'line_total', 'real_unit_cost', 'real_line_total']
        read_only_fields = ['id', 'line_total', 'real_unit_cost', 'real_line_total']

    def get_line_total(self, obj):
        return obj.line_total

    def get_real_unit_cost(self, obj):
        return obj.real_unit_cost

    def get_real_line_total(self, obj):
        return obj.real_line_total


class PurchaseReceiptSerializer(serializers.ModelSerializer):
    items = PurchaseReceiptItemSerializer(many=True)
    total_cost = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseReceipt
        fields = [
            'id', 'purchase_order', 'reference', 'received_date', 'status',
            'notes', 'transport_cost', 'customs_cost', 'handling_cost', 'insurance_cost', 'other_cost',
            'total_cost', 'items', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'received_date', 'created_at', 'updated_at', 'total_cost']

    def get_total_cost(self, obj):
        return obj.total_cost

    def validate(self, attrs):
        items = attrs.get('items')
        if not items:
            raise serializers.ValidationError({'items': 'Au moins un produit doit être reçu.'})

        purchase_order = attrs.get('purchase_order')
        if purchase_order is not None:
            order_item_products = {item.product_id for item in purchase_order.items.all()}
            received_products = {item['product'].id for item in items if 'product' in item}
            if not received_products.issubset(order_item_products):
                raise serializers.ValidationError({'items': 'Un produit reçu ne correspond pas à la commande fournisseur.'})

        for item in items:
            if item.get('quantity_received', 0) <= 0:
                raise serializers.ValidationError({'items': 'La quantité reçue doit être strictement positive.'})

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        user = self.context.get('request').user if self.context.get('request') else None
        purchase_receipt = PurchaseReceipt.objects.create(**validated_data)

        for item_data in items_data:
            PurchaseReceiptItem.objects.create(purchase_receipt=purchase_receipt, **item_data)

        default_location = InventoryLocation.objects.filter(location_type='warehouse').first()
        if default_location is None:
            default_location = InventoryLocation.objects.create(
                name='Entrepôt principal',
                code='WH-DEFAULT',
                location_type='warehouse',
                address='Stock par défaut',
            )

        for item_data in items_data:
            product = item_data['product']
            quantity = item_data['quantity_received']
            stock_item, _ = StockItem.objects.get_or_create(product=product, location=default_location)
            stock_item.quantity += quantity
            stock_item.save(update_fields=['quantity', 'updated_at'])

            product.quantity = (product.quantity or 0) + quantity
            quantity_decimal = Decimal(quantity)
            acquisition_costs = sum([
                Decimal(str(purchase_receipt.transport_cost)),
                Decimal(str(purchase_receipt.customs_cost)),
                Decimal(str(purchase_receipt.handling_cost)),
                Decimal(str(purchase_receipt.insurance_cost)),
                Decimal(str(purchase_receipt.other_cost)),
            ])
            product.cost_price = Decimal(str(item_data['unit_cost'])) + acquisition_costs / quantity_decimal
            product.purchase_price = item_data['unit_cost']
            product.save(update_fields=['quantity', 'cost_price', 'purchase_price', 'updated_at'])

            StockMovement.objects.create(
                product=product,
                location=default_location,
                movement_type='in',
                quantity=quantity,
                reference=purchase_receipt.reference,
                notes='Réception fournisseur',
                created_by=user,
            )

        if purchase_receipt.purchase_order:
            order = purchase_receipt.purchase_order
            received_totals = {}
            for receipt in order.receipts.prefetch_related('items').all():
                for receipt_item in receipt.items.all():
                    received_totals[receipt_item.product_id] = received_totals.get(receipt_item.product_id, 0) + receipt_item.quantity_received

            is_complete = all(
                received_totals.get(order_item.product_id, 0) >= order_item.quantity
                for order_item in order.items.all()
            )
            order.status = 'received' if is_complete else 'partial_received'
            order.save(update_fields=['status', 'updated_at'])
            purchase_receipt.status = 'received' if is_complete else 'partial'
            purchase_receipt.save(update_fields=['status', 'updated_at'])

        return purchase_receipt
