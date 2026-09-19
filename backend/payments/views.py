from django.db.models import Count, F, Max, Sum
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from sales.models import Sale
from users.permissions import SensitiveMutationPermission, role_permission
from core.idempotency import replay_idempotent_request, store_idempotent_response
from .models import CreditLedger, Payment
from .serializers import CreditLedgerSerializer, PaymentSerializer


def credit_sales_queryset():
    return Sale.objects.filter(payment_method='credit')


class PaymentListCreateView(generics.ListCreateAPIView):
    queryset = Payment.objects.select_related('customer', 'sale').all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('payments')]

    def create(self, request, *args, **kwargs):
        endpoint = request.path
        key, replay = replay_idempotent_request(request, endpoint)
        if replay is not None:
            return replay
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        response = Response(serializer.data, status=status.HTTP_201_CREATED)
        store_idempotent_response(request, endpoint, key, response)
        return response


class PaymentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Payment.objects.select_related('customer', 'sale').all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('payments'), SensitiveMutationPermission]

    def destroy(self, request, *args, **kwargs):
        return Response(
            {'detail': 'La suppression physique d’un paiement est interdite.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class PaymentReceiptView(generics.GenericAPIView):
    queryset = Payment.objects.select_related('customer', 'sale').all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('payments')]

    def get(self, request, *args, **kwargs):
        payment = self.get_object()
        return Response({
            'type': 'payment_receipt',
            'payment_id': payment.id,
            'reference': payment.reference,
            'customer': payment.customer.full_name,
            'sale_id': payment.sale_id,
            'amount': str(payment.amount),
            'payment_method': payment.payment_method,
            'payment_date': payment.payment_date,
        }, status=status.HTTP_200_OK)


class CustomerPaymentSummaryView(generics.GenericAPIView):
    serializer_class = CreditLedgerSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('payments')]

    def get(self, request, customer_id):
        customer_sales = credit_sales_queryset().filter(customer_id=customer_id)
        sales_total = customer_sales.aggregate(total=Sum('total_amount'))['total'] or 0
        total_paid = customer_sales.aggregate(total=Sum('amount_paid'))['total'] or 0
        balance = max(sales_total - total_paid, 0)

        return Response({
            'customer_id': customer_id,
            'sales_count': customer_sales.count(),
            'sales_total': sales_total,
            'total_paid': total_paid,
            'balance': balance,
            'status': 'settled' if balance == 0 else ('partial' if total_paid else 'unpaid'),
        }, status=status.HTTP_200_OK)


class CreditListView(generics.GenericAPIView):
    serializer_class = CreditLedgerSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('payments')]

    def get(self, request, *args, **kwargs):
        credits = credit_sales_queryset().values('customer_id').annotate(
            customer_name=F('customer__full_name'),
            sales_count=Count('id'),
            total_credit=Sum('total_amount'),
            total_paid=Sum('amount_paid'),
            last_payment=Max('payments__payment_date'),
        ).order_by('customer_id')

        result = []
        for credit in credits:
            total_credit = credit['total_credit'] or 0
            total_paid = credit['total_paid'] or 0
            result.append({
                'customer_id': credit['customer_id'],
                'customer_name': credit['customer_name'],
                'sales_count': credit['sales_count'],
                'total_credit': total_credit,
                'total_paid': total_paid,
                'balance': max(total_credit - total_paid, 0),
                'last_payment': credit['last_payment'],
                'status': 'settled' if total_credit <= total_paid else ('partial' if total_paid else 'unpaid'),
            })
        return Response(result, status=status.HTTP_200_OK)


class CustomerCreditDetailView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, role_permission('payments')]

    def get(self, request, customer_id):
        sales = credit_sales_queryset().filter(customer_id=customer_id).select_related('customer', 'invoice')
        if not sales.exists():
            return Response({'detail': 'Aucune vente à crédit pour ce client.'}, status=status.HTTP_404_NOT_FOUND)

        customer = sales.first().customer
        payments = Payment.objects.filter(customer_id=customer_id, sale__in=sales).order_by('-payment_date')
        total_credit = sales.aggregate(total=Sum('total_amount'))['total'] or 0
        total_paid = sales.aggregate(total=Sum('amount_paid'))['total'] or 0
        history = []
        for sale in sales.order_by('-sale_date'):
            sale_paid = sale.amount_paid
            invoice = getattr(sale, 'invoice', None)
            history.append({
                'sale_id': sale.id,
                'invoice_number': invoice.invoice_number if invoice else None,
                'date': sale.sale_date,
                'total_credit': sale.total_amount,
                'total_paid': sale_paid,
                'balance': max(sale.total_amount - sale_paid, 0),
            })

        return Response({
            'customer': {
                'id': customer.id,
                'full_name': customer.full_name,
                'phone': customer.phone,
                'email': customer.email,
            },
            'sales_count': sales.count(),
            'total_credit': total_credit,
            'total_paid': total_paid,
            'balance': max(total_credit - total_paid, 0),
            'status': 'settled' if total_credit <= total_paid else ('partial' if total_paid else 'unpaid'),
            'sales': history,
            'payments': PaymentSerializer(payments, many=True).data,
        }, status=status.HTTP_200_OK)
