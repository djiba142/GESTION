from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from core.models import AuditLog
from customers.models import Customer
from notifications.models import Notification
from sales.models import Sale
from users.models import User


class PaymentApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='paiement_manager',
            password='secret123',
            pin_code='1234',
            role='manager',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.customer = Customer.objects.create(full_name='Fode Diaby', phone='+224600003000')
        self.sale = Sale.objects.create(
            customer=self.customer,
            status='paid',
            payment_method='credit',
            total_amount='500000.00',
            amount_paid='250000.00',
        )

    def test_create_payment_registers_credit_reduction(self):
        response = self.client.post(
            '/api/payments/',
            {
                'customer': self.customer.id,
                'sale': self.sale.id,
                'amount': '250000.00',
                'payment_method': 'cash',
                'reference': 'PAY-001',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(float(response.data['amount']), 250000.0)

    def test_credit_balance_is_calculated(self):
        response = self.client.get(f'/api/payments/customer/{self.customer.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('balance', response.data)

    def test_payment_creation_registers_audit_log(self):
        initial_count = AuditLog.objects.filter(action='payment').count()

        response = self.client.post(
            '/api/payments/',
            {
                'customer': self.customer.id,
                'sale': self.sale.id,
                'amount': '5000.00',
                'payment_method': 'cash',
                'reference': 'PAY-TRACE-001',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(AuditLog.objects.filter(action='payment').count(), initial_count + 1)

    def test_payment_creation_creates_internal_admin_notification(self):
        response = self.client.post(
            '/api/payments/',
            {
                'customer': self.customer.id,
                'sale': self.sale.id,
                'amount': '15000.00',
                'payment_method': 'cash',
                'reference': 'PAY-ADMIN-NOTIF',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            Notification.objects.filter(
                sale=self.sale,
                event_type='payment_received',
                channel='internal',
                status='sent',
            ).exists()
        )

    def test_credit_summary_excludes_cash_sales_and_aggregates_multiple_credit_sales(self):
        Sale.objects.create(
            customer=self.customer,
            status='paid',
            payment_method='cash',
            total_amount='900000.00',
            amount_paid='900000.00',
        )
        second_credit_sale = Sale.objects.create(
            customer=self.customer,
            status='partial',
            payment_method='credit',
            total_amount='300000.00',
            amount_paid='0.00',
        )
        response = self.client.get(f'/api/payments/customer/{self.customer.id}/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['sales_count'], 2)
        self.assertEqual(Decimal(str(response.data['sales_total'])), Decimal('800000'))
        self.assertEqual(Decimal(str(response.data['balance'])), Decimal('550000'))

        Sale.objects.create(
            customer=self.customer,
            status='partial',
            payment_method='credit',
            total_amount='200000.00',
            amount_paid='0.00',
        )
        list_response = self.client.get('/api/payments/credits/')

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(Decimal(str(list_response.data[0]['balance'])), Decimal('750000'))

    def test_credit_detail_exposes_sales_and_payment_history(self):
        credit_sale = Sale.objects.create(
            customer=self.customer,
            status='partial',
            payment_method='credit',
            total_amount='500000.00',
            amount_paid='0.00',
        )
        self.client.post(
            '/api/payments/',
            {
                'customer': self.customer.id,
                'sale': credit_sale.id,
                'amount': '150000.00',
                'payment_method': 'cash',
                'reference': 'PAY-HISTORY-001',
            },
            format='json',
        )
        response = self.client.get(f'/api/payments/customer/{self.customer.id}/credits/')

        self.assertEqual(Decimal(str(response.data['balance'])), Decimal('600000'))
        self.assertEqual(len(response.data['sales']), 2)
        self.assertEqual(len(response.data['payments']), 1)
