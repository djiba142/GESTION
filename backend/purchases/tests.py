from django.test import TestCase
from rest_framework.test import APIClient

from core.models import AuditLog
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

    def test_purchase_order_actions_follow_business_transitions(self):
        response = self.client.post(
            '/api/v1/purchase-orders/',
            {
                'supplier': self.supplier.id,
                'reference': 'PO-ACTIONS-001',
                'items': [{'product': self.product.id, 'quantity': 2, 'unit_cost': '100000.00'}],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        order_id = response.data['id']

        self.assertEqual(self.client.post(f'/api/v1/purchase-orders/{order_id}/send/', format='json').status_code, 200)
        self.assertEqual(self.client.post(f'/api/v1/purchase-orders/{order_id}/confirm/', format='json').status_code, 200)
        self.assertEqual(self.client.post(f'/api/v1/purchase-orders/{order_id}/close/', format='json').status_code, 200)
        self.assertEqual(self.client.post(f'/api/v1/purchase-orders/{order_id}/send/', format='json').status_code, 409)

    def test_create_then_validate_purchase_receipt_updates_stock_and_costs(self):
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
        self.assertEqual(response.data['status'], 'draft')
        self.assertFalse(self.product.stock_items.exists())

        validation = self.client.post(f"/api/v1/receipts/{response.data['id']}/validate/", format='json')
        self.assertEqual(validation.status_code, 200)
        self.assertEqual(validation.data['status'], 'received')
        self.assertEqual(self.product.stock_items.get().quantity, 4)

        repeated_validation = self.client.post(f"/api/v1/receipts/{response.data['id']}/validate/", format='json')
        self.assertEqual(repeated_validation.status_code, 409)
        self.assertTrue(AuditLog.objects.filter(model_name='PurchaseReceipt', action='stock', record_id=response.data['id']).exists())

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
        self.assertEqual(response.data['status'], 'draft')
        order_detail = self.client.get(f"/api/purchases/orders/{order_response.data['id']}/")
        self.assertEqual(order_detail.data['status'], 'approved')

    def test_acquisition_costs_endpoint_exposes_real_costs(self):
        order_response = self.client.post(
            '/api/v1/purchase-orders/',
            {
                'supplier': self.supplier.id,
                'reference': 'PO-2026-ACQ',
                'items': [{'product': self.product.id, 'quantity': 2, 'unit_cost': '150000.00'}],
            },
            format='json',
        )

        receipt_response = self.client.post(
            '/api/v1/receipts/',
            {
                'purchase_order': order_response.data['id'],
                'reference': 'RCPT-2026-ACQ',
                'items': [{'product': self.product.id, 'quantity_received': 2, 'unit_cost': '150000.00'}],
                'transport_cost': '5000.00',
                'customs_cost': '3000.00',
            },
            format='json',
        )

        self.assertEqual(receipt_response.status_code, 201)

        response = self.client.get('/api/v1/acquisition-costs/')
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.data['count'], 1)

        detail_response = self.client.get(f"/api/v1/acquisition-costs/{receipt_response.data['id']}/")
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(float(detail_response.data['total_cost']), 308000.0)
        self.assertEqual(float(detail_response.data['items'][0]['real_unit_cost']), 154000.0)

    def test_acquisition_costs_endpoint_supports_create_and_patch(self):
        order_response = self.client.post(
            '/api/v1/purchase-orders/',
            {
                'supplier': self.supplier.id,
                'reference': 'PO-2026-ACQ-UPDATE',
                'items': [{'product': self.product.id, 'quantity': 2, 'unit_cost': '150000.00'}],
            },
            format='json',
        )

        create_response = self.client.post(
            '/api/v1/acquisition-costs/',
            {
                'purchase_order': order_response.data['id'],
                'reference': 'RCPT-2026-ACQ-UPDATE',
                'items': [{'product': self.product.id, 'quantity_received': 2, 'unit_cost': '150000.00'}],
                'transport_cost': '5000.00',
                'customs_cost': '3000.00',
            },
            format='json',
        )

        self.assertEqual(create_response.status_code, 201)

        patch_response = self.client.patch(
            f"/api/v1/acquisition-costs/{create_response.data['id']}/",
            {'transport_cost': '8000.00'},
            format='json',
        )

        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(float(patch_response.data['transport_cost']), 8000.0)
