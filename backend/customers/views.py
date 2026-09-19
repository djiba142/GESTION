from django.db.models import Q, Sum
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from users.permissions import role_permission
from .models import Customer
from .serializers import CustomerSerializer
from core.serializers import JsonResponseSerializer


class CustomerListCreateView(generics.ListCreateAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('customers')]

    def get_queryset(self):
        queryset = Customer.objects.all()
        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search) |
                Q(phone__icontains=search) |
                Q(email__icontains=search) |
                Q(company_name__icontains=search)
            )
        return queryset


class CustomerDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('customers')]


class CustomerSalesHistoryView(generics.GenericAPIView):
    serializer_class = JsonResponseSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('customers')]

    def get(self, request, pk):
        from sales.models import Sale

        sales = Sale.objects.filter(customer_id=pk).values(
            'id', 'sale_date', 'status', 'total_amount', 'amount_paid',
        )
        return Response(list(sales), status=status.HTTP_200_OK)


class CustomerInvoicesHistoryView(generics.GenericAPIView):
    serializer_class = JsonResponseSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('customers')]

    def get(self, request, pk):
        from sales.models import Invoice

        invoices = Invoice.objects.filter(sale__customer_id=pk).values(
            'id', 'invoice_number', 'qr_code', 'issue_date', 'total_amount', 'paid_amount',
        )
        return Response(list(invoices), status=status.HTTP_200_OK)


class CustomerPaymentsHistoryView(generics.GenericAPIView):
    serializer_class = JsonResponseSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('customers')]

    def get(self, request, pk):
        from payments.models import Payment

        payments = Payment.objects.filter(customer_id=pk).values(
            'id', 'sale_id', 'amount', 'payment_method', 'reference', 'payment_date',
        )
        return Response(list(payments), status=status.HTTP_200_OK)


class CustomerCreditView(generics.GenericAPIView):
    serializer_class = JsonResponseSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('customers')]

    def get(self, request, pk):
        from payments.models import Payment
        from sales.models import Sale

        sales_total = Sale.objects.filter(customer_id=pk).aggregate(total=Sum('total_amount'))['total'] or 0
        paid_total = Payment.objects.filter(customer_id=pk).aggregate(total=Sum('amount'))['total'] or 0
        return Response({
            'customer_id': pk,
            'total_credit': float(sales_total),
            'total_paid': float(paid_total),
            'balance': float(sales_total - paid_total),
        }, status=status.HTTP_200_OK)
