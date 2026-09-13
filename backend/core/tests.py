from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from customers.models import Customer
from payments.models import Payment
from products.models import Product
from sales.models import Sale
from users.models import User
from .models import AppSetting, AuditLog


class CoreApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='admin_core',
            password='secret123',
            pin_code='1234',
            role='admin',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_list_and_create_app_settings(self):
        response = self.client.post(
            '/api/core/settings/',
            {'key': 'company_name', 'value': 'NEXORA', 'description': 'Nom de la société'},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(AppSetting.objects.count(), 1)

        list_response = self.client.get('/api/core/settings/')
        self.assertEqual(list_response.status_code, 200)
        self.assertTrue(any(item['key'] == 'company_name' for item in list_response.data))

    def test_list_audit_logs(self):
        AuditLog.objects.create(
            user=self.user,
            action='login',
            model_name='User',
            record_id=self.user.id,
            details='Connexion de l’administrateur',
        )

        response = self.client.get('/api/core/audit/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(item['action'] == 'login' for item in response.data))

    def test_dashboard_summary_exposes_business_kpis(self):
        customer = Customer.objects.create(full_name='Aminata Diallo', phone='+224600000001')
        product = Product.objects.create(
            sku='SKU-001',
            name='Produit dashboard',
            brand='NEXORA',
            selling_price=Decimal('5000.00'),
            quantity=4,
            alert_threshold=5,
        )
        sale = Sale.objects.create(
            customer=customer,
            status='partial',
            payment_method='cash',
            total_amount=Decimal('150000.00'),
            amount_paid=Decimal('100000.00'),
        )
        Payment.objects.create(
            customer=customer,
            sale=sale,
            amount=Decimal('100000.00'),
            payment_method='cash',
            reference='PAY-DASH-001',
        )

        response = self.client.get('/api/core/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total_products'], 1)
        self.assertEqual(response.data['total_customers'], 1)
        self.assertEqual(response.data['total_sales'], 150000.0)
        self.assertEqual(response.data['total_received'], 100000.0)
        self.assertEqual(response.data['outstanding_balance'], 50000.0)
        self.assertEqual(response.data['low_stock_products'], 1)
        self.assertEqual(response.data['total_stock_items'], product.quantity)

    def test_advanced_reporting_api_is_available(self):
        customer = Customer.objects.create(full_name='Aissatou Barry', phone='+224600000002')
        Product.objects.create(
            sku='SKU-REPORT-1',
            name='Produit report',
            brand='NEXORA',
            selling_price=Decimal('20000.00'),
            quantity=10,
            alert_threshold=2,
        )
        sale = Sale.objects.create(
            customer=customer,
            status='paid',
            payment_method='cash',
            total_amount=Decimal('20000.00'),
            amount_paid=Decimal('20000.00'),
        )
        Payment.objects.create(
            customer=customer,
            sale=sale,
            amount=Decimal('20000.00'),
            payment_method='cash',
            reference='PAY-REPORT-001',
        )

        response = self.client.get('/api/core/reports/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('summary', response.data)
        self.assertIn('top_products', response.data)
        self.assertIn('sales_by_period', response.data)
        self.assertIn('customer_breakdown', response.data)
        self.assertIn('inventory_status', response.data)

    def test_cashflow_summary_exposes_financial_snapshot(self):
        customer = Customer.objects.create(full_name='Saliou Camara', phone='+224600000010')
        sale = Sale.objects.create(
            customer=customer,
            status='paid',
            payment_method='cash',
            total_amount=Decimal('300000.00'),
            amount_paid=Decimal('300000.00'),
        )
        Payment.objects.create(
            customer=customer,
            sale=sale,
            amount=Decimal('300000.00'),
            payment_method='cash',
            reference='PAY-CASHFLOW-001',
        )

        response = self.client.get('/api/core/cashflow/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['cash_in'], 300000.0)
        self.assertEqual(response.data['cash_out'], 0.0)
        self.assertEqual(response.data['net_cash'], 300000.0)

    def test_advanced_reporting_filters_by_date_and_customer(self):
        customer_recent = Customer.objects.create(full_name='Recent Client', phone='+224600000011')
        customer_old = Customer.objects.create(full_name='Old Client', phone='+224600000012')
        product = Product.objects.create(
            sku='SKU-FILT-001',
            name='Produit filtré',
            brand='NEXORA',
            selling_price=Decimal('60000.00'),
            quantity=10,
            alert_threshold=2,
        )

        recent_sale = Sale.objects.create(
            customer=customer_recent,
            status='paid',
            payment_method='cash',
            total_amount=Decimal('60000.00'),
            amount_paid=Decimal('60000.00'),
        )
        recent_sale.items.create(product=product, quantity=1, unit_price=Decimal('60000.00'))
        recent_sale.sale_date = timezone.now()
        recent_sale.save(update_fields=['sale_date'])

        old_sale = Sale.objects.create(
            customer=customer_old,
            status='paid',
            payment_method='bank_transfer',
            total_amount=Decimal('100000.00'),
            amount_paid=Decimal('100000.00'),
        )
        old_sale.items.create(product=product, quantity=1, unit_price=Decimal('100000.00'))
        old_sale.sale_date = timezone.now() - timedelta(days=30)
        old_sale.save(update_fields=['sale_date'])

        response = self.client.get(
            '/api/core/reports/',
            {'start_date': (timezone.now() - timedelta(days=1)).date().isoformat(), 'end_date': timezone.now().date().isoformat(), 'customer': customer_recent.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['summary']['total_sales'], 60000.0)
        self.assertEqual(response.data['summary']['total_customers'], 1)

    def test_global_search_returns_cross_module_results(self):
        customer = Customer.objects.create(full_name='Aminata Diop', phone='+224600000020')
        product = Product.objects.create(
            sku='PRD-SEARCH-001',
            name='Produit global',
            brand='NEXORA',
            selling_price=Decimal('25000.00'),
            quantity=7,
            alert_threshold=2,
        )
        sale = Sale.objects.create(
            customer=customer,
            status='paid',
            payment_method='cash',
            total_amount=Decimal('25000.00'),
            amount_paid=Decimal('25000.00'),
        )
        sale.items.create(product=product, quantity=1, unit_price=Decimal('25000.00'))
        Payment.objects.create(
            customer=customer,
            sale=sale,
            amount=Decimal('25000.00'),
            payment_method='cash',
            reference='PAY-SEARCH-001',
        )

        response = self.client.get('/api/core/search/', {'q': 'PRD-SEARCH-001'})

        self.assertEqual(response.status_code, 200)
        self.assertIn('products', response.data)
        self.assertIn('customers', response.data)
        self.assertIn('payments', response.data)
        self.assertTrue(any(item['sku'] == 'PRD-SEARCH-001' for item in response.data['products']))

    def test_app_settings_require_admin_role(self):
        manager = User.objects.create_user(
            username='manager_app',
            password='secret123',
            pin_code='4321',
            role='manager',
        )
        client = APIClient()
        client.force_authenticate(user=manager)

        response = client.post(
            '/api/core/settings/',
            {'key': 'finance_mode', 'value': 'strict'},
            format='json',
        )

        self.assertEqual(response.status_code, 403)
