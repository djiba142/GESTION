from datetime import datetime, time

from django.db.models import DecimalField, F, Q, Sum, ExpressionWrapper
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from customers.models import Customer
from expenses.models import Expense
from inventory.models import Carton
from payments.models import Payment
from products.models import Product
from sales.models import Invoice, Sale, SaleItem
from suppliers.models import Supplier
from users.permissions import IsAdminUser, SensitiveMutationPermission, role_permission
from .models import AppSetting, AuditLog, Company
from .serializers import AppSettingSerializer, AuditLogSerializer, CompanySerializer, JsonResponseSerializer


class AuditLogListView(generics.ListAPIView):
    queryset = AuditLog.objects.select_related('user').all()
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('core')]


class AppSettingListCreateView(generics.ListCreateAPIView):
    queryset = AppSetting.objects.all()
    serializer_class = AppSettingSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]


class AppSettingDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = AppSetting.objects.all()
    serializer_class = AppSettingSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser, SensitiveMutationPermission]


class CompanyView(generics.RetrieveUpdateAPIView):
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('core'), SensitiveMutationPermission]

    def get_object(self):
        company, _ = Company.objects.get_or_create(id=1, defaults={'name': 'NEXORA'})
        return company


class DashboardSummaryView(generics.GenericAPIView):
    serializer_class = JsonResponseSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('core')]

    def get(self, request, *args, **kwargs):
        total_products = Product.objects.filter(is_active=True).count()
        total_customers = Customer.objects.filter(is_active=True).count()
        total_sales = Sale.objects.aggregate(total=Sum('total_amount'))['total'] or 0
        total_received = Payment.objects.aggregate(total=Sum('amount'))['total'] or 0
        total_open_balance = float(total_sales) - float(total_received)
        low_stock_products = Product.objects.filter(is_active=True, quantity__lte=F('alert_threshold')).count()

        summary = {
            'total_products': total_products,
            'total_customers': total_customers,
            'total_sales': float(total_sales),
            'total_received': float(total_received),
            'outstanding_balance': float(total_open_balance),
            'low_stock_products': low_stock_products,
            'total_stock_items': Product.objects.filter(is_active=True).aggregate(total=Sum('quantity'))['total'] or 0,
        }
        return Response(summary, status=status.HTTP_200_OK)


class AdvancedReportingView(generics.GenericAPIView):
    serializer_class = JsonResponseSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('core')]

    def get(self, request, *args, **kwargs):
        start_date = request.query_params.get('start_date') or request.query_params.get('date_from')
        end_date = request.query_params.get('end_date') or request.query_params.get('date_to')
        customer_id = request.query_params.get('customer')
        product_id = request.query_params.get('product')
        category_id = request.query_params.get('category')
        location_id = request.query_params.get('location')
        seller_id = request.query_params.get('seller')

        sales_queryset = Sale.objects.select_related('customer').all()
        if start_date:
            start_dt = parse_date(start_date)
            if start_dt:
                start_boundary = datetime.combine(start_dt, time.min)
                if timezone.is_naive(start_boundary):
                    start_boundary = timezone.make_aware(start_boundary)
                sales_queryset = sales_queryset.filter(sale_date__gte=start_boundary)
        if end_date:
            end_dt = parse_date(end_date)
            if end_dt:
                end_boundary = datetime.combine(end_dt, time.max)
                if timezone.is_naive(end_boundary):
                    end_boundary = timezone.make_aware(end_boundary)
                sales_queryset = sales_queryset.filter(sale_date__lte=end_boundary)
        if customer_id:
            sales_queryset = sales_queryset.filter(customer_id=customer_id)
        if seller_id:
            sales_queryset = sales_queryset.filter(seller_id=seller_id)
        if location_id:
            sales_queryset = sales_queryset.filter(location_id=location_id)
        if product_id:
            sales_queryset = sales_queryset.filter(items__product_id=product_id).distinct()
        if category_id:
            sales_queryset = sales_queryset.filter(items__product__category_id=category_id).distinct()

        total_sales = sales_queryset.aggregate(total=Sum('total_amount'))['total'] or 0
        total_received = Payment.objects.filter(sale__in=sales_queryset.values_list('id', flat=True)).aggregate(total=Sum('amount'))['total'] or 0
        total_cost = SaleItem.objects.filter(sale__in=sales_queryset.values_list('id', flat=True)).aggregate(
            total=Sum(ExpressionWrapper(F('quantity') * F('product__cost_price'), output_field=DecimalField(max_digits=14, decimal_places=2)))
        )['total'] or 0
        total_customers = sales_queryset.values('customer').distinct().count()
        total_products = Product.objects.filter(is_active=True).count()

        top_products = list(
            Product.objects.filter(is_active=True)
            .order_by('-quantity')[:5]
            .values('id', 'name', 'sku', 'quantity', 'selling_price')
        )

        customer_breakdown = list(
            sales_queryset.values('customer_id', 'customer__full_name')
            .annotate(total_paid=Sum('total_amount'))
            .values('customer_id', 'customer__full_name', 'total_paid')
            .order_by('-total_paid')[:10]
        )

        inventory_status = {
            'total_stock_items': Product.objects.filter(is_active=True).aggregate(total=Sum('quantity'))['total'] or 0,
            'low_stock_products': Product.objects.filter(is_active=True, quantity__lte=F('alert_threshold')).count(),
            'healthy_products': Product.objects.filter(is_active=True, quantity__gt=F('alert_threshold')).count(),
        }

        sales_by_period = [
            {
                'period': 'total_sales',
                'value': float(total_sales),
            },
            {
                'period': 'received',
                'value': float(total_received),
            },
            {
                'period': 'customers',
                'value': float(total_customers),
            },
            {
                'period': 'products',
                'value': float(total_products),
            },
        ]

        payload = {
            'summary': {
                'total_sales': float(total_sales),
                'total_received': float(total_received),
                'outstanding_balance': float(total_sales) - float(total_received),
                'total_cost': float(total_cost),
                'gross_margin': float(total_sales) - float(total_cost),
                'total_customers': total_customers,
                'total_products': total_products,
            },
            'top_products': top_products,
            'sales_by_period': sales_by_period,
            'customer_breakdown': customer_breakdown,
            'inventory_status': inventory_status,
        }
        return Response(payload, status=status.HTTP_200_OK)


class CashflowSummaryView(generics.GenericAPIView):
    serializer_class = JsonResponseSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('core')]

    def get(self, request, *args, **kwargs):
        cash_in = Payment.objects.aggregate(total=Sum('amount'))['total'] or 0
        cash_out = Expense.objects.aggregate(total=Sum('amount'))['total'] or 0
        net_cash = float(cash_in) - float(cash_out)

        return Response({
            'cash_in': float(cash_in),
            'cash_out': float(cash_out),
            'net_cash': net_cash,
        }, status=status.HTTP_200_OK)


class CashView(CashflowSummaryView):
    pass


class CashTransactionsView(generics.GenericAPIView):
    serializer_class = JsonResponseSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('core')]

    def get(self, request, *args, **kwargs):
        payments = [
            {
                'type': 'in',
                'id': payment.id,
                'reference': payment.reference,
                'amount': float(payment.amount),
                'date': payment.payment_date,
                'description': f'Paiement {payment.reference or payment.id}',
            }
            for payment in Payment.objects.all()
        ]
        expenses = [
            {
                'type': 'out',
                'id': expense.id,
                'reference': expense.reference,
                'amount': float(expense.amount),
                'date': expense.expense_date,
                'description': expense.title,
            }
            for expense in Expense.objects.all()
        ]
        transactions = sorted(payments + expenses, key=lambda item: item['date'], reverse=True)
        return Response(transactions, status=status.HTTP_200_OK)


class FinancialSummaryView(CashflowSummaryView):
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        total_sales = Sale.objects.aggregate(total=Sum('total_amount'))['total'] or 0
        total_received = Payment.objects.aggregate(total=Sum('amount'))['total'] or 0
        response.data['outstanding_balance'] = float(total_sales - total_received)
        return response


class GlobalSearchView(generics.GenericAPIView):
    serializer_class = JsonResponseSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('core')]

    def get(self, request, *args, **kwargs):
        query = (request.query_params.get('q') or request.query_params.get('query') or '').strip()
        if not query:
            return Response({
                'query': '',
                'total': 0,
                'products': [],
                'customers': [],
                'suppliers': [],
                'invoices': [],
                'cartons': [],
                'sales': [],
                'payments': [],
            }, status=status.HTTP_200_OK)

        q_filter = Q(name__icontains=query) | Q(sku__icontains=query) | Q(barcode__icontains=query) | Q(qr_code__icontains=query)
        products = list(
            Product.objects.filter(q_filter).values('id', 'sku', 'name', 'brand', 'quantity', 'selling_price', 'barcode', 'qr_code')[:10]
        )

        customer_filter = Q(full_name__icontains=query) | Q(phone__icontains=query) | Q(email__icontains=query) | Q(company_name__icontains=query)
        customers = list(
            Customer.objects.filter(customer_filter).values('id', 'full_name', 'phone', 'email', 'company_name')[:10]
        )

        supplier_filter = Q(name__icontains=query) | Q(contact_name__icontains=query) | Q(company_name__icontains=query) | Q(phone__icontains=query)
        suppliers = list(
            Supplier.objects.filter(supplier_filter).values('id', 'name', 'contact_name', 'company_name', 'phone', 'email')[:10]
        )

        invoice_filter = Q(invoice_number__icontains=query) | Q(sale__customer__full_name__icontains=query)
        invoices = list(
            Invoice.objects.filter(invoice_filter).select_related('sale__customer').values('id', 'invoice_number', 'total_amount', 'paid_amount', 'sale__customer__full_name')[:10]
        )

        payment_filter = Q(reference__icontains=query) | Q(customer__full_name__icontains=query) | Q(customer__phone__icontains=query)
        payments = list(
            Payment.objects.filter(payment_filter).select_related('customer').values('id', 'reference', 'amount', 'payment_method', 'customer__full_name')[:10]
        )

        carton_filter = Q(reference__icontains=query) | Q(qr_code__icontains=query) | Q(product__name__icontains=query)
        cartons = list(
            Carton.objects.filter(carton_filter).select_related('product', 'location').values(
                'id', 'reference', 'qr_code', 'quantity', 'product__name', 'location__name',
            )[:10]
        )

        sale_filter = Q(notes__icontains=query) | Q(external_reference__icontains=query) | Q(customer__full_name__icontains=query)
        if query.isdigit():
            sale_filter |= Q(id=int(query))
        sales = list(
            Sale.objects.filter(sale_filter).values('id', 'status', 'total_amount', 'amount_paid', 'customer__full_name')[:10]
        )

        payload = {
            'query': query,
            'total': len(products) + len(customers) + len(suppliers) + len(invoices) + len(cartons) + len(sales) + len(payments),
            'products': products,
            'customers': customers,
            'suppliers': suppliers,
            'invoices': invoices,
            'cartons': cartons,
            'sales': sales,
            'payments': payments,
        }
        return Response(payload, status=status.HTTP_200_OK)
