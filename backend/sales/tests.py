from django.test import TestCase
from rest_framework.test import APIClient

from customers.models import Customer
from products.models import Product
from users.models import User


class SaleApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='vente_manager',
            password='secret123',
            pin_code='1234',
            role='manager',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.customer = Customer.objects.create(full_name='Ali Kaba', phone='+224600002000')
        self.product = Product.objects.create(
            sku='SALE-001',
            name='Smartphone X',
            purchase_price='200000',
            selling_price='300000',
            quantity=10,
            alert_threshold=2,
        )

    def test_create_sale_and_invoice(self):
        payload = {
            'customer': self.customer.id,
            'status': 'paid',
            'payment_method': 'cash',
            'items': [
                {'product': self.product.id, 'quantity': 2, 'unit_price': '300000.00'}
            ],
        }
        response = self.client.post('/api/sales/', payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(float(response.data['total_amount']), 600000.0)
        self.assertTrue(response.data['invoice_number'])

    def test_sale_rejects_unavailable_stock(self):
        self.product.quantity = 1
        self.product.save()

        response = self.client.post(
            '/api/sales/',
            {
                'customer': self.customer.id,
                'status': 'paid',
                'payment_method': 'cash',
                'items': [{'product': self.product.id, 'quantity': 2, 'unit_price': '300000.00'}],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('quantity', response.data)

    def test_invoice_generates_qr_code_when_missing(self):
        payload = {
            'customer': self.customer.id,
            'status': 'paid',
            'payment_method': 'cash',
            'items': [
                {'product': self.product.id, 'quantity': 1, 'unit_price': '300000.00'}
            ],
        }

        response = self.client.post('/api/sales/', payload, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['invoice_number'])
        sale = self.client.get(f"/api/sales/{response.data['id']}/")
        self.assertTrue(sale.data['invoice_qr_code'])
        self.assertTrue(sale.data['invoice_qr_code'].startswith('NEXORA-INV-'))
