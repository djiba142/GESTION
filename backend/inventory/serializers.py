from django.core.exceptions import ValidationError
from rest_framework import serializers

from products.models import Product
from .models import Carton, InventoryLocation, StockItem, StockMovement, StockTransfer


class InventoryLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryLocation
        fields = ['id', 'name', 'code', 'location_type', 'address', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class StockItemSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    location_name = serializers.SerializerMethodField()

    class Meta:
        model = StockItem
        fields = ['id', 'product', 'product_name', 'location', 'location_name', 'quantity', 'updated_at']
        read_only_fields = ['id', 'updated_at']

    def get_product_name(self, obj):
        return obj.product.name if obj.product else None

    def get_location_name(self, obj):
        return obj.location.name if obj.location else None


class StockMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    location_name = serializers.SerializerMethodField()

    class Meta:
        model = StockMovement
        fields = [
            'id', 'product', 'product_name', 'location', 'location_name',
            'movement_type', 'quantity', 'reference', 'notes', 'created_by', 'created_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'product_name', 'location_name']

    def get_product_name(self, obj):
        return obj.product.name if obj.product else None

    def get_location_name(self, obj):
        return obj.location.name if obj.location else None

    def validate(self, attrs):
        product = attrs.get('product')
        location = attrs.get('location')
        quantity = attrs.get('quantity', 0)
        movement_type = attrs.get('movement_type')

        if quantity <= 0:
            raise serializers.ValidationError({'quantity': 'La quantité doit être strictement positive.'})

        if not product or not location:
            raise serializers.ValidationError('Produit et emplacement sont obligatoires.')

        stock_item, _ = StockItem.objects.get_or_create(product=product, location=location)

        if movement_type == 'out' and stock_item.quantity - quantity < 0:
            raise serializers.ValidationError({'quantity': 'La quantité sortante dépasse le stock disponible.'})

        return attrs

    def create(self, validated_data):
        product = validated_data['product']
        location = validated_data['location']
        quantity = validated_data['quantity']
        movement_type = validated_data['movement_type']
        created_by = validated_data.get('created_by')

        stock_item, _ = StockItem.objects.get_or_create(product=product, location=location)

        if movement_type == 'in':
            stock_item.quantity += quantity
        elif movement_type == 'out':
            if stock_item.quantity - quantity < 0:
                raise ValidationError('La quantité en stock ne peut pas devenir négative.')
            stock_item.quantity -= quantity
        elif movement_type == 'adjustment':
            stock_item.quantity = quantity
        else:
            raise ValidationError('Type de mouvement non supporté.')

        stock_item.save(update_fields=['quantity', 'updated_at'])

        movement_data = dict(validated_data)
        movement_data.pop('created_by', None)

        movement = StockMovement.objects.create(
            created_by=created_by,
            **movement_data,
        )
        return movement


class StockTransferSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    from_location_name = serializers.SerializerMethodField()
    to_location_name = serializers.SerializerMethodField()

    class Meta:
        model = StockTransfer
        fields = [
            'id', 'product', 'product_name', 'from_location', 'from_location_name',
            'to_location', 'to_location_name', 'quantity', 'reference', 'status',
            'notes', 'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status', 'created_by', 'created_at', 'updated_at', 'product_name', 'from_location_name', 'to_location_name']

    def get_product_name(self, obj):
        return obj.product.name if obj.product else None

    def get_from_location_name(self, obj):
        return obj.from_location.name if obj.from_location else None

    def get_to_location_name(self, obj):
        return obj.to_location.name if obj.to_location else None

    def validate(self, attrs):
        product = attrs.get('product')
        from_location = attrs.get('from_location')
        to_location = attrs.get('to_location')
        quantity = attrs.get('quantity', 0)

        if not product or not from_location or not to_location:
            raise serializers.ValidationError('Produit et emplacements sont obligatoires.')
        if from_location == to_location:
            raise serializers.ValidationError({'to_location': 'La destination doit être différente de l’origine.'})
        if quantity <= 0:
            raise serializers.ValidationError({'quantity': 'La quantité du transfert doit être strictement positive.'})

        source_item = StockItem.objects.filter(product=product, location=from_location).first()
        if not source_item or source_item.quantity < quantity:
            raise serializers.ValidationError({'quantity': 'La quantité demandée dépasse le stock disponible dans l’emplacement source.'})

        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        created_by = request.user if request and getattr(request, 'user', None) else None
        validated_data.pop('created_by', None)

        transfer = StockTransfer.objects.create(created_by=created_by, **validated_data)

        source_item, _ = StockItem.objects.get_or_create(product=transfer.product, location=transfer.from_location)
        destination_item, _ = StockItem.objects.get_or_create(product=transfer.product, location=transfer.to_location)

        if source_item.quantity < transfer.quantity:
            raise ValidationError('La quantité en stock source est insuffisante pour ce transfert.')

        source_item.quantity -= transfer.quantity
        source_item.save(update_fields=['quantity', 'updated_at'])

        destination_item.quantity += transfer.quantity
        destination_item.save(update_fields=['quantity', 'updated_at'])

        StockMovement.objects.create(
            product=transfer.product,
            location=transfer.from_location,
            movement_type='out',
            quantity=transfer.quantity,
            reference=transfer.reference,
            notes=f'Transfert vers {transfer.to_location.name}',
            created_by=created_by,
        )
        StockMovement.objects.create(
            product=transfer.product,
            location=transfer.to_location,
            movement_type='in',
            quantity=transfer.quantity,
            reference=transfer.reference,
            notes=f'Transfert depuis {transfer.from_location.name}',
            created_by=created_by,
        )

        return transfer


class CartonSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    location_name = serializers.SerializerMethodField()

    class Meta:
        model = Carton
        fields = [
            'id', 'product', 'product_name', 'location', 'location_name',
            'reference', 'quantity', 'items_per_carton', 'qr_code', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'qr_code', 'created_at', 'updated_at', 'product_name', 'location_name']

    def get_product_name(self, obj):
        return obj.product.name if obj.product else None

    def get_location_name(self, obj):
        return obj.location.name if obj.location else None

    def validate(self, attrs):
        product = attrs.get('product')
        location = attrs.get('location')
        quantity = attrs.get('quantity', 0)
        items_per_carton = attrs.get('items_per_carton', 0)

        if not product or not location:
            raise serializers.ValidationError('Produit et emplacement sont obligatoires.')
        if quantity <= 0:
            raise serializers.ValidationError({'quantity': 'La quantité du carton doit être strictement positive.'})
        if items_per_carton <= 0:
            raise serializers.ValidationError({'items_per_carton': 'Le nombre d’éléments par carton doit être positif.'})
        return attrs

    def create(self, validated_data):
        carton = Carton.objects.create(**validated_data)
        carton.generate_qr_code()
        carton.save(update_fields=['qr_code'])
        return carton
