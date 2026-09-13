from rest_framework import generics, permissions

from sales.models import Invoice
from users.permissions import role_permission

from .serializers import InvoiceSerializer


class InvoiceListView(generics.ListAPIView):
    queryset = Invoice.objects.select_related('sale__customer').all()
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('sales')]


class InvoiceDetailView(generics.RetrieveAPIView):
    queryset = Invoice.objects.select_related('sale__customer').all()
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('sales')]
