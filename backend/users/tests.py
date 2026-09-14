from django.test import TestCase
from rest_framework.test import APIClient

from core.models import AuditLog
from customers.models import Customer
from payments.models import Payment
from sales.models import Sale
from .models import User


class AuthLoginTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='vendeur1',
            email='vendeur1@example.com',
            password='secret123',
            phone='+224600000001',
            pin_code='1234',
            role='sales',
        )

    def test_login_with_username_and_pin(self):
        response = self.client.post('/api/users/login/', {'identifier': 'vendeur1', 'pin': '1234'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['user']['username'], 'vendeur1')
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.pin_code, '1234')

    def test_login_with_phone_and_pin(self):
        response = self.client.post('/api/users/login/', {'identifier': '+224600000001', 'pin': '1234'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['user']['phone'], '+224600000001')

    def test_login_rejects_wrong_pin(self):
        response = self.client.post('/api/users/login/', {'identifier': 'vendeur1', 'pin': '9999'}, format='json')
        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.data['success'])

    def test_successful_login_creates_audit_log(self):
        response = self.client.post('/api/users/login/', {'identifier': 'vendeur1', 'pin': '1234'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(AuditLog.objects.filter(user=self.user, action='login').exists())

    def test_user_list_requires_admin_role(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/users/')
        self.assertEqual(response.status_code, 403)

    def test_user_profile_exposes_preferred_language(self):
        self.user.preferred_language = 'en'
        self.user.save(update_fields=['preferred_language'])
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/api/users/me/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['preferred_language'], 'en')

    def test_user_cannot_elevate_own_role_from_profile(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            '/api/users/me/',
            {'role': 'admin', 'is_active': False},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, 'sales')
        self.assertTrue(self.user.is_active)

    def test_user_gets_locked_after_repeated_failed_pin_attempts(self):
        for attempt in range(4):
            response = self.client.post('/api/users/login/', {'identifier': 'vendeur1', 'pin': '9999'}, format='json')
            self.assertEqual(response.status_code, 401)
            self.assertIn('Code PIN incorrect', response.data['message'])

        response = self.client.post('/api/users/login/', {'identifier': 'vendeur1', 'pin': '9999'}, format='json')

        self.assertEqual(response.status_code, 403)
        self.assertIn('bloqué', response.data['message'])

        response = self.client.post('/api/users/login/', {'identifier': 'vendeur1', 'pin': '1234'}, format='json')
        self.assertEqual(response.status_code, 403)
        self.assertIn('bloqué', response.data['message'])

    def test_user_can_switch_language_and_keyboard_layout_globally(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            '/api/users/me/',
            {'preferred_language': 'en', 'keyboard_layout': 'us'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.preferred_language, 'en')
        self.assertEqual(self.user.keyboard_layout, 'us')
        self.assertEqual(self.client.session.get('django_language'), 'en')

    def test_admin_can_list_users(self):
        admin_user = User.objects.create_user(
            username='admin1',
            email='admin1@example.com',
            password='secret123',
            phone='+224600000002',
            pin_code='4321',
            role='admin',
        )
        self.client.force_authenticate(user=admin_user)
        response = self.client.get('/api/users/')
        self.assertEqual(response.status_code, 200)

    def test_admin_can_fetch_and_update_user_detail_from_v1_api(self):
        admin_user = User.objects.create_user(
            username='admin_detail',
            email='admin_detail@example.com',
            password='secret123',
            phone='+224600000007',
            pin_code='4321',
            role='admin',
        )
        self.client.force_authenticate(user=admin_user)

        response = self.client.get(f'/api/v1/users/{self.user.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['username'], 'vendeur1')

        patch_response = self.client.patch(
            f'/api/v1/users/{self.user.id}/',
            {'role': 'manager'},
            format='json',
        )
        self.assertEqual(patch_response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, 'manager')
        self.assertTrue(AuditLog.objects.filter(model_name='User', action='update', record_id=self.user.id).exists())

    def test_sales_user_cannot_create_products(self):
        sales_user = User.objects.create_user(
            username='sales_user',
            email='sales_user@example.com',
            password='secret123',
            phone='+224600000003',
            pin_code='5678',
            role='sales',
        )
        self.client.force_authenticate(user=sales_user)
        response = self.client.post(
            '/api/products/',
            {
                'sku': 'SKU-SEC-01',
                'name': 'Produit interdit',
                'brand': 'NEXORA',
                'selling_price': '15000.00',
                'quantity': 10,
                'alert_threshold': 2,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_stock_user_cannot_access_payment_creation(self):
        stock_user = User.objects.create_user(
            username='stock_user',
            email='stock_user@example.com',
            password='secret123',
            phone='+224600000004',
            pin_code='9999',
            role='stock',
        )
        customer = self.user
        self.client.force_authenticate(user=stock_user)
        response = self.client.post(
            '/api/payments/',
            {
                'customer': customer.id,
                'amount': '5000.00',
                'payment_method': 'cash',
                'reference': 'PAY-SEC-001',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_sales_user_cannot_update_sensitive_payment(self):
        sales_user = User.objects.create_user(
            username='sales_user_sensitive',
            email='sales_sensitive@example.com',
            password='secret123',
            phone='+224600000005',
            pin_code='1111',
            role='sales',
        )
        customer = Customer.objects.create(full_name='Client sensible')
        sale = Sale.objects.create(customer=customer, total_amount='1000.00', amount_paid='0.00')
        payment = Payment.objects.create(customer=customer, sale=sale, amount='500.00', payment_method='cash', reference='PAY-SENSITIVE-001')

        self.client.force_authenticate(user=sales_user)
        response = self.client.patch(
            f'/api/payments/{payment.id}/',
            {'amount': '750.00'},
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_manager_can_update_sensitive_payment(self):
        manager_user = User.objects.create_user(
            username='manager_sensitive',
            email='manager_sensitive@example.com',
            password='secret123',
            phone='+224600000006',
            pin_code='2222',
            role='manager',
        )
        customer = Customer.objects.create(full_name='Client gestionnaire')
        sale = Sale.objects.create(customer=customer, total_amount='1000.00', amount_paid='0.00')
        payment = Payment.objects.create(customer=customer, sale=sale, amount='500.00', payment_method='cash', reference='PAY-SENSITIVE-002')

        self.client.force_authenticate(user=manager_user)
        response = self.client.patch(
            f'/api/payments/{payment.id}/',
            {'amount': '750.00'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
