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

    def test_external_sale_endpoint_forces_external_flag(self):
        from suppliers.models import Supplier

        supplier = Supplier.objects.create(name='Fournisseur externe')
        response = self.client.post(
            '/api/v1/sales/external/',
            {
                'customer': self.customer.id,
                'external_supplier': supplier.id,
                'external_reference': 'EXT-001',
                'status': 'paid',
                'payment_method': 'cash',
                'items': [{'product': self.product.id, 'quantity': 1, 'unit_price': '300000.00'}],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['is_external'])

    def test_sale_with_location_decrements_location_stock(self):
        from inventory.models import InventoryLocation, StockItem

        location = InventoryLocation.objects.create(name='Boutique vente', code='SALE-LOCATION')
        StockItem.objects.create(product=self.product, location=location, quantity=3)

        response = self.client.post(
            '/api/v1/sales/',
            {
                'customer': self.customer.id,
                'location': location.id,
                'status': 'paid',
                'payment_method': 'cash',
                'items': [{'product': self.product.id, 'quantity': 2, 'unit_price': '300000.00'}],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(StockItem.objects.get(product=self.product, location=location).quantity, 1)

    def test_sale_delete_is_rejected(self):
        response = self.client.post(
            '/api/sales/',
            {
                'customer': self.customer.id,
                'status': 'paid',
                'payment_method': 'cash',
                'items': [{'product': self.product.id, 'quantity': 1, 'unit_price': '300000.00'}],
            },
            format='json',
        )

        delete_response = self.client.delete(f"/api/sales/{response.data['id']}/")
        self.assertEqual(delete_response.status_code, 405)

    def test_sale_idempotency_replays_same_response(self):
        payload = {
            'customer': self.customer.id,
            'status': 'paid',
            'payment_method': 'cash',
            'items': [{'product': self.product.id, 'quantity': 1, 'unit_price': '300000.00'}],
        }
        first = self.client.post('/api/v1/sales/', payload, format='json', HTTP_IDEMPOTENCY_KEY='SALE-ONCE-001')
        second = self.client.post('/api/v1/sales/', payload, format='json', HTTP_IDEMPOTENCY_KEY='SALE-ONCE-001')

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.data['id'], first.data['id'])
