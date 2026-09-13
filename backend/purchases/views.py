from rest_framework import generics, permissions

from users.permissions import role_permission
from .models import PurchaseOrder, PurchaseReceipt
from .serializers import PurchaseOrderSerializer, PurchaseReceiptSerializer


class PurchaseOrderListCreateView(generics.ListCreateAPIView):
    queryset = PurchaseOrder.objects.select_related('supplier').prefetch_related('items__product').all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('purchases')]


class PurchaseOrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PurchaseOrder.objects.select_related('supplier').prefetch_related('items__product').all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('purchases')]


class PurchaseReceiptListCreateView(generics.ListCreateAPIView):
    queryset = PurchaseReceipt.objects.select_related('purchase_order__supplier').prefetch_related('items__product').all()
    serializer_class = PurchaseReceiptSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('purchases')]


class PurchaseReceiptDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PurchaseReceipt.objects.select_related('purchase_order__supplier').prefetch_related('items__product').all()
    serializer_class = PurchaseReceiptSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('purchases')]
