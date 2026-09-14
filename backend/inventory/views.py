from django.core.exceptions import ValidationError
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from core.models import AuditLog
from users.permissions import SensitiveMutationPermission, role_permission
from .models import Carton, InventoryLocation, StockItem, StockMovement, StockTransfer
from .serializers import CartonSerializer, InventoryLocationSerializer, StockItemSerializer, StockMovementSerializer, StockTransferSerializer, transition_stock_transfer


def accessible_locations(user):
    locations = InventoryLocation.objects.all()
    if getattr(user, 'role', None) in {'admin', 'manager'} or getattr(user, 'is_superuser', False):
        return locations
    if InventoryLocation.objects.filter(authorized_users__isnull=False).exists():
        return locations.filter(authorized_users=user)
    return locations


class InventoryLocationListCreateView(generics.ListCreateAPIView):
    queryset = InventoryLocation.objects.all()
    serializer_class = InventoryLocationSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('inventory')]

    def get_queryset(self):
        return accessible_locations(self.request.user)

    def perform_create(self, serializer):
        location = serializer.save()
        if getattr(self.request.user, 'role', None) not in {'admin', 'manager'}:
            location.authorized_users.add(self.request.user)


class InventoryLocationDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = InventoryLocation.objects.all()
    serializer_class = InventoryLocationSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('inventory'), SensitiveMutationPermission]

    def get_queryset(self):
        return accessible_locations(self.request.user)

    def destroy(self, request, *args, **kwargs):
        return Response(
            {'detail': 'La suppression physique d’un emplacement est interdite.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class StockItemListView(generics.ListAPIView):
    queryset = StockItem.objects.select_related('product', 'location').all()
    serializer_class = StockItemSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('inventory')]

    def get_queryset(self):
        return StockItem.objects.select_related('product', 'location').filter(
            location__in=accessible_locations(self.request.user),
        )


class InventoryLocationStockView(generics.GenericAPIView):
    serializer_class = StockItemSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('inventory')]

    def get(self, request, pk):
        location = accessible_locations(request.user).filter(pk=pk).first()
        if location is None:
            return Response({'detail': 'Emplacement introuvable ou non autorisé.'}, status=status.HTTP_404_NOT_FOUND)
        items = StockItem.objects.filter(location=location).select_related('product')
        return Response({
            'location': location.id,
            'location_name': location.name,
            'total_quantity': sum(item.quantity for item in items),
            'items': [
                {
                    'product': item.product_id,
                    'product_name': item.product.name,
                    'quantity': item.quantity,
                }
                for item in items
            ],
        }, status=status.HTTP_200_OK)


class StockMovementListCreateView(generics.ListCreateAPIView):
    queryset = StockMovement.objects.select_related('product', 'location', 'created_by').all()
    serializer_class = StockMovementSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('inventory')]

    def get_queryset(self):
        return StockMovement.objects.select_related('product', 'location', 'created_by').filter(
            location__in=accessible_locations(self.request.user),
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            self.perform_create(serializer)
        except ValidationError as exc:
            return Response({'quantity': [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)

        movement = serializer.instance
        AuditLog.objects.create(
            user=request.user,
            action='stock',
            model_name='StockMovement',
            record_id=movement.id,
            details=f"Mouvement de stock {movement.movement_type}: {movement.reference}",
        )

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class StockMovementDetailView(generics.RetrieveAPIView):
    queryset = StockMovement.objects.select_related('product', 'location', 'created_by').all()
    serializer_class = StockMovementSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('inventory')]


class StockTransferListCreateView(generics.ListCreateAPIView):
    queryset = StockTransfer.objects.select_related('product', 'from_location', 'to_location', 'created_by').all()
    serializer_class = StockTransferSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('inventory')]

    def get_queryset(self):
        locations = accessible_locations(self.request.user)
        return StockTransfer.objects.select_related('product', 'from_location', 'to_location', 'created_by').filter(
            from_location__in=locations,
            to_location__in=locations,
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        try:
            self.perform_create(serializer)
        except ValidationError as exc:
            return Response({'quantity': [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class StockTransferDetailView(generics.RetrieveAPIView):
    queryset = StockTransfer.objects.select_related('product', 'from_location', 'to_location', 'created_by').all()
    serializer_class = StockTransferSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('inventory')]


class StockTransferActionView(generics.GenericAPIView):
    queryset = StockTransfer.objects.select_related('product', 'from_location', 'to_location').all()
    serializer_class = StockTransferSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('inventory')]

    @extend_schema(operation_id='stock_transfer_action')
    def post(self, request, action, *args, **kwargs):
        transfer = self.get_object()
        target_status = {'validate': 'validated', 'ship': 'shipped', 'receive': 'received'}.get(action)
        if target_status is None:
            return Response({'detail': 'Action de transfert inconnue.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            transition_stock_transfer(transfer, target_status, request.user)
        except ValidationError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)

        AuditLog.objects.create(
            user=request.user,
            action='stock',
            model_name='StockTransfer',
            record_id=transfer.id,
            details=f"Transfert de stock {action}: {transfer.reference}",
        )
        return Response(self.get_serializer(transfer).data, status=status.HTTP_200_OK)


class CartonListCreateView(generics.ListCreateAPIView):
    queryset = Carton.objects.select_related('product', 'location').all()
    serializer_class = CartonSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('inventory')]

    def get_queryset(self):
        return Carton.objects.select_related('product', 'location').filter(
            location__in=accessible_locations(self.request.user),
        )


class CartonDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Carton.objects.select_related('product', 'location').all()
    serializer_class = CartonSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('inventory'), SensitiveMutationPermission]

    def get_queryset(self):
        return Carton.objects.select_related('product', 'location').filter(
            location__in=accessible_locations(self.request.user),
        )


class CartonQrView(generics.GenericAPIView):
    queryset = Carton.objects.select_related('product', 'location').all()
    serializer_class = CartonSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('inventory')]

    def get(self, request, *args, **kwargs):
        carton = self.get_object()
        return Response({
            'type': 'carton',
            'id': carton.id,
            'reference': carton.reference,
            'product': carton.product_id,
            'product_name': carton.product.name,
            'location': carton.location_id,
            'qr_code': carton.qr_code,
        }, status=status.HTTP_200_OK)


class QrResolveView(generics.GenericAPIView):
    from core.serializers import JsonResponseSerializer

    serializer_class = JsonResponseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        from products.models import Product
        from sales.models import Invoice

        code = (request.query_params.get('code') or '').strip()
        if not code:
            return Response({'code': ['Le code est requis.']}, status=status.HTTP_400_BAD_REQUEST)

        product = Product.objects.filter(qr_code=code).first() or Product.objects.filter(barcode=code).first() or Product.objects.filter(sku=code).first()
        if product:
            return Response({'type': 'product', 'id': product.id, 'qr_code': product.qr_code}, status=status.HTTP_200_OK)

        carton = Carton.objects.filter(qr_code=code).first() or Carton.objects.filter(reference=code).first()
        if carton:
            return Response({'type': 'carton', 'id': carton.id, 'qr_code': carton.qr_code}, status=status.HTTP_200_OK)

        invoice = Invoice.objects.filter(qr_code=code).first() or Invoice.objects.filter(invoice_number=code).first()
        if invoice:
            return Response({'type': 'invoice', 'id': invoice.id, 'qr_code': invoice.qr_code}, status=status.HTTP_200_OK)

        return Response({'detail': 'Ressource introuvable pour ce code.'}, status=status.HTTP_404_NOT_FOUND)
