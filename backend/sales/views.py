from rest_framework import generics, permissions, status
from rest_framework.response import Response

from users.permissions import SensitiveMutationPermission, role_permission
from .models import Sale
from .serializers import SaleSerializer


class SaleListCreateView(generics.ListCreateAPIView):
    queryset = Sale.objects.select_related('customer').prefetch_related('items__product').all()
    serializer_class = SaleSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('sales')]


class SaleDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Sale.objects.select_related('customer').prefetch_related('items__product').all()
    serializer_class = SaleSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('sales'), SensitiveMutationPermission]
