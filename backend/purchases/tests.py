from django.test import TestCase
from rest_framework.test import APIClient

from products.models import Product
from suppliers.models import Supplier
from users.models import User


class PurchaseOrderApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='achats_manager',
            password='secret123',
            pin_code='1234',
            role='manager',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.supplier = Supplier.objects.create(
            name='Alpha Distribution',
            contact_name='Moussa Bah',
            phone='+224600001000',
            email='moussa@alpha.sn',
            company_name='Alpha Distribution',
        )
        self.product = Product.objects.create(
            sku='ACH-001',
            name='Ordinateur portable',
            purchase_price='300000',
            selling_price='450000',
            quantity=0,
            alert_threshold=2,
        )

    def test_create_purchase_order_with_items(self):
        payload = {
            'supplier': self.supplier.id,
            'reference': 'PO-2026-001',
            'status': 'draft',
            'notes': 'Commande initiale',
            'items': [
                {'product': self.product.id, 'quantity': 3, 'unit_cost': '250000.00'}
            ],
        }
        response = self.client.post('/api/purchases/orders/', payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['reference'], 'PO-2026-001')
        self.assertEqual(float(response.data['total_amount']), 750000.0)

    def test_list_purchase_orders(self):
        self.client.post(
            '/api/purchases/orders/',
            {
                'supplier': self.supplier.id,
                'reference': 'PO-2026-002',
                'status': 'draft',
                'items': [{'product': self.product.id, 'quantity': 2, 'unit_cost': '100000.00'}],
            },
            format='json',
        )
        response = self.client.get('/api/purchases/orders/')
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 1)

    def test_create_purchase_receipt_updates_stock_and_costs(self):
        order = self.client.post(
            '/api/purchases/orders/',
            {
                'supplier': self.supplier.id,
                'reference': 'PO-2026-003',
                'status': 'approved',
                'items': [{'product': self.product.id, 'quantity': 4, 'unit_cost': '200000.00'}],
            },
            format='json',
        )

        response = self.client.post(
            '/api/purchases/receipts/',
            {
                'purchase_order': order.data['id'],
                'reference': 'RCPT-2026-001',
                'received_date': '2026-09-12T10:00:00Z',
                'status': 'received',
                'items': [
                    {'product': self.product.id, 'quantity_received': 4, 'unit_cost': '200000.00'}
                ],
                'transport_cost': '5000.00',
                'customs_cost': '3000.00',
                'insurance_cost': '2000.00',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(float(response.data['total_cost']), 810000.0)
        self.assertEqual(float(response.data['items'][0]['real_unit_cost']), 202500.0)
        self.assertEqual(response.data['status'], 'received')
        self.assertEqual(self.product.stock_items.get().quantity, 4)

    def test_partial_receipt_keeps_order_open(self):
        order_response = self.client.post(
            '/api/purchases/orders/',
            {
                'supplier': self.supplier.id,
                'reference': 'PO-2026-PARTIAL',
                'status': 'approved',
                'items': [{'product': self.product.id, 'quantity': 10, 'unit_cost': '200000.00'}],
            },
            format='json',
        )

        response = self.client.post(
            '/api/purchases/receipts/',
            {
                'purchase_order': order_response.data['id'],
                'reference': 'RCPT-2026-PARTIAL',
                'items': [{'product': self.product.id, 'quantity_received': 4, 'unit_cost': '200000.00'}],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], 'partial')
        order_detail = self.client.get(f"/api/purchases/orders/{order_response.data['id']}/")
        self.assertEqual(order_detail.data['status'], 'partial_received')
