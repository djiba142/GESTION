from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.db import transaction
from drf_spectacular.utils import extend_schema

from core.models import AuditLog
from users.permissions import role_permission
from .models import PurchaseOrder, PurchaseReceipt
from .serializers import PurchaseOrderSerializer, PurchaseReceiptSerializer, validate_purchase_receipt


class PurchaseOrderListCreateView(generics.ListCreateAPIView):
    queryset = PurchaseOrder.objects.select_related('supplier').prefetch_related('items__product').all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('purchases')]


class PurchaseOrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PurchaseOrder.objects.select_related('supplier').prefetch_related('items__product').all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('purchases')]


class PurchaseOrderActionView(generics.GenericAPIView):
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('purchases')]

    @extend_schema(operation_id='purchase_order_action')
    @transaction.atomic
    def post(self, request, action, *args, **kwargs):
        order = PurchaseOrder.objects.select_for_update().get(pk=kwargs['pk'])
        transitions = {
            'send': ('draft', 'submitted'),
            'confirm': ('submitted', 'approved'),
            'close': (('approved', 'partial_received', 'received'), 'received'),
        }
        transition = transitions.get(action)
        if transition is None:
            return Response({'detail': 'Action de commande inconnue.'}, status=status.HTTP_404_NOT_FOUND)

        expected, target = transition
        if order.status not in (expected if isinstance(expected, tuple) else (expected,)):
            return Response(
                {'detail': f'La commande ne peut pas passer à l’état {target} depuis {order.status}.'},
                status=status.HTTP_409_CONFLICT,
            )

        order.status = target
        order.save(update_fields=['status', 'updated_at'])
        return Response(self.get_serializer(order).data, status=status.HTTP_200_OK)


class PurchaseReceiptListCreateView(generics.ListCreateAPIView):
    queryset = PurchaseReceipt.objects.select_related('purchase_order__supplier').prefetch_related('items__product').all()
    serializer_class = PurchaseReceiptSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('purchases')]


class AcquisitionCostListView(generics.ListCreateAPIView):
    queryset = PurchaseReceipt.objects.select_related('purchase_order__supplier').prefetch_related('items__product').all()
    serializer_class = PurchaseReceiptSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('purchases')]


class AcquisitionCostDetailView(generics.RetrieveUpdateAPIView):
    queryset = PurchaseReceipt.objects.select_related('purchase_order__supplier').prefetch_related('items__product').all()
    serializer_class = PurchaseReceiptSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('purchases')]


class PurchaseReceiptDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PurchaseReceipt.objects.select_related('purchase_order__supplier').prefetch_related('items__product').all()
    serializer_class = PurchaseReceiptSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('purchases')]


class PurchaseReceiptValidateView(generics.GenericAPIView):
    queryset = PurchaseReceipt.objects.select_related('purchase_order').prefetch_related('items__product').all()
    serializer_class = PurchaseReceiptSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('purchases')]

    def post(self, request, *args, **kwargs):
        receipt = self.get_object()
        if receipt.status != 'draft':
            return Response(
                {'detail': 'Cette réception a déjà été validée.'},
                status=status.HTTP_409_CONFLICT,
            )
        validate_purchase_receipt(receipt, request.user)
        AuditLog.objects.create(
            user=request.user,
            action='stock',
            model_name='PurchaseReceipt',
            record_id=receipt.id,
            details=f"Réception fournisseur validée: {receipt.reference}",
        )
        return Response(self.get_serializer(receipt).data, status=status.HTTP_200_OK)
