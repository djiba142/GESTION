from django.test import TestCase
from rest_framework.test import APIClient

from core.models import AuditLog
from customers.models import Customer
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
