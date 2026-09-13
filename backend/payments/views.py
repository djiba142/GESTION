from django.db.models import Sum
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from sales.models import Sale
from users.permissions import SensitiveMutationPermission, role_permission
from .models import Payment
from .serializers import PaymentSerializer


class PaymentListCreateView(generics.ListCreateAPIView):
    queryset = Payment.objects.select_related('customer', 'sale').all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('payments')]


class PaymentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Payment.objects.select_related('customer', 'sale').all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('payments'), SensitiveMutationPermission]


class CustomerPaymentSummaryView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, role_permission('payments')]

    def get(self, request, customer_id):
        customer_sales = Sale.objects.filter(customer_id=customer_id)
        sales_total = customer_sales.aggregate(total=Sum('total_amount'))['total'] or 0
        total_paid = Payment.objects.filter(customer_id=customer_id).aggregate(total=Sum('amount'))['total'] or 0
        balance = float(sales_total) - float(total_paid)

        return Response({
            'customer_id': customer_id,
            'sales_total': float(sales_total),
            'total_paid': float(total_paid),
            'balance': balance,
        }, status=status.HTTP_200_OK)
