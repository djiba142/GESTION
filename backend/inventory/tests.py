from django.test import TestCase
from rest_framework.test import APIClient

from products.models import Product
from users.models import User
from .models import InventoryLocation, StockItem, StockMovement, StockTransfer


class InventoryApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='stock_manager',
            password='secret123',
            pin_code='1234',
            role='stock',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.product = Product.objects.create(
            sku='INV-100',
            name='Sac à dos Pro',
            purchase_price='50000',
            selling_price='85000',
            quantity=0,
            alert_threshold=5,
        )

    def test_create_stock_location(self):
        payload = {
            'name': 'Entrepôt central',
            'code': 'ENT-01',
            'location_type': 'warehouse',
            'address': 'Conakry',
        }
        response = self.client.post('/api/inventory/locations/', payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(InventoryLocation.objects.count(), 1)
        self.assertEqual(response.data['code'], 'ENT-01')

    def test_create_stock_in_movement_updates_quantity(self):
        location = InventoryLocation.objects.create(name='Boutique', code='SHOP-01', location_type='shop')
        response = self.client.post(
            '/api/inventory/movements/',
            {
                'product': self.product.id,
                'location': location.id,
                'movement_type': 'in',
                'quantity': 25,
                'reference': 'RECEPTION-001',
                'notes': 'Réception initiale',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(StockMovement.objects.count(), 1)
        self.assertEqual(StockItem.objects.get(product=self.product, location=location).quantity, 25)

    def test_out_movement_cannot_make_stock_negative(self):
        location = InventoryLocation.objects.create(name='Boutique', code='SHOP-02', location_type='shop')
        StockItem.objects.create(product=self.product, location=location, quantity=5)

        response = self.client.post(
            '/api/inventory/movements/',
            {
                'product': self.product.id,
                'location': location.id,
                'movement_type': 'out',
                'quantity': 8,
                'reference': 'VENTE-001',
                'notes': 'Sortie non autorisée',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('quantity', response.data)

    def test_create_stock_transfer_updates_source_and_destination(self):
        source = InventoryLocation.objects.create(name='Entrepôt central', code='ENT-01', location_type='warehouse')
        destination = InventoryLocation.objects.create(name='Boutique principale', code='SHOP-01', location_type='shop')
        StockItem.objects.create(product=self.product, location=source, quantity=20)
        StockItem.objects.create(product=self.product, location=destination, quantity=0)

        response = self.client.post(
            '/api/inventory/transfers/',
            {
                'product': self.product.id,
                'from_location': source.id,
                'to_location': destination.id,
                'quantity': 8,
                'reference': 'TR-001',
                'notes': 'Transfert magasin',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(StockTransfer.objects.count(), 1)
        self.assertEqual(StockItem.objects.get(product=self.product, location=source).quantity, 12)
        self.assertEqual(StockItem.objects.get(product=self.product, location=destination).quantity, 8)

    def test_stock_transfer_rejects_insufficient_source_quantity(self):
        source = InventoryLocation.objects.create(name='Entrepôt central', code='ENT-02', location_type='warehouse')
        destination = InventoryLocation.objects.create(name='Boutique secondaire', code='SHOP-02', location_type='shop')
        StockItem.objects.create(product=self.product, location=source, quantity=3)
        StockItem.objects.create(product=self.product, location=destination, quantity=0)

        response = self.client.post(
            '/api/inventory/transfers/',
            {
                'product': self.product.id,
                'from_location': source.id,
                'to_location': destination.id,
                'quantity': 5,
                'reference': 'TR-002',
                'notes': 'Transfert interdit',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('quantity', response.data)

    def test_create_carton_and_generate_qr_code(self):
        location = InventoryLocation.objects.create(name='Boutique principale', code='SHOP-03', location_type='shop')
        self.product.quantity = 30
        self.product.save(update_fields=['quantity'])

        response = self.client.post(
            '/api/inventory/cartons/',
            {
                'product': self.product.id,
                'location': location.id,
                'reference': 'CTN-000125',
                'quantity': 10,
                'items_per_carton': 5,
                'notes': 'Carton de stock',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['qr_code'].startswith('NEXORA-CTN-'))
        self.assertEqual(response.data['reference'], 'CTN-000125')

    def test_scan_qr_code_returns_product_metadata(self):
        product = Product.objects.create(
            sku='QR-010',
            name='Produit scannable',
            purchase_price='20000',
            selling_price='35000',
            quantity=4,
            alert_threshold=1,
        )

        response = self.client.get('/api/products/scan/', {'code': product.qr_code})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['sku'], 'QR-010')
        self.assertEqual(response.data['name'], 'Produit scannable')
