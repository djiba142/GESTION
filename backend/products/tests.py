from django.test import TestCase
from rest_framework.test import APIClient

from users.models import User
from .models import Category, Product


class ProductApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='manager1',
            password='secret123',
            pin_code='1234',
            role='manager',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.category = Category.objects.create(name='Électronique', description='Produits tech')

    def test_create_product(self):
        payload = {
            'sku': 'PRD-001',
            'name': 'Laptop Pro',
            'category': self.category.id,
            'brand': 'NEXORA',
            'unit': 'piece',
            'purchase_price': '500000',
            'selling_price': '750000',
            'currency': 'GNF',
            'quantity': 12,
            'alert_threshold': 3,
            'barcode': '123456789',
            'qr_code': 'qr-001',
            'image': 'https://example.com/laptop.png',
        }
        response = self.client.post('/api/products/', payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(response.data['name'], 'Laptop Pro')

    def test_list_products(self):
        Product.objects.create(
            sku='PRD-002',
            name='Téléphone X',
            category=self.category,
            purchase_price='250000',
            selling_price='350000',
            quantity=8,
            alert_threshold=2,
        )
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 1)

    def test_search_product_by_name_or_sku(self):
        Product.objects.create(
            sku='PRD-003',
            name='Casque Bluetooth',
            category=self.category,
            purchase_price='100000',
            selling_price='180000',
            quantity=5,
            alert_threshold=1,
        )
        response = self.client.get('/api/products/?search=Bluetooth')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(item['name'] == 'Casque Bluetooth' for item in response.data))

    def test_product_generates_qr_code_when_missing(self):
        product = Product.objects.create(
            sku='PRD-QR-001',
            name='Scanner USB',
            category=self.category,
            purchase_price='120000',
            selling_price='180000',
            quantity=5,
            alert_threshold=1,
            qr_code='',
        )

        self.assertTrue(product.qr_code)
        self.assertTrue(product.qr_code.startswith('NEXORA-'))

    def test_product_label_endpoint_returns_printable_metadata(self):
        product = Product.objects.create(
            sku='PRD-LABEL-001',
            name='Étiquette Produit',
            category=self.category,
            purchase_price='150000',
            selling_price='210000',
            quantity=7,
            alert_threshold=2,
            barcode='987654321',
            qr_code='',
        )

        response = self.client.post(f'/api/products/{product.id}/label/', format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['sku'], 'PRD-LABEL-001')
        self.assertEqual(response.data['name'], 'Étiquette Produit')
        self.assertTrue(response.data['qr_code'].startswith('NEXORA-'))
        self.assertEqual(response.data['selling_price'], '210000.00')

    def test_product_can_be_archived_without_being_deleted(self):
        product = Product.objects.create(
            sku='PRD-ARCHIVE-001',
            name='Produit à archiver',
            quantity=4,
        )

        response = self.client.post(f'/api/products/{product.id}/archive/', format='json')

        self.assertEqual(response.status_code, 200)
        product.refresh_from_db()
        self.assertFalse(product.is_active)
        self.assertTrue(Product.objects.filter(pk=product.id).exists())

    def test_product_delete_is_rejected(self):
        product = Product.objects.create(sku='PRD-NODELETE-001', name='Produit protégé')

        response = self.client.delete(f'/api/products/{product.id}/')

        self.assertEqual(response.status_code, 405)
        self.assertTrue(Product.objects.filter(pk=product.id).exists())

    def test_product_quantity_cannot_be_changed_directly(self):
        product = Product.objects.create(
            sku='PRD-QUANTITY-LOCK',
            name='Produit quantité protégée',
            quantity=8,
        )

        response = self.client.patch(
            f'/api/products/{product.id}/',
            {'quantity': 99},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        product.refresh_from_db()
        self.assertEqual(product.quantity, 8)

    def test_product_stock_returns_quantities_by_location(self):
        from inventory.models import InventoryLocation, StockItem

        product = Product.objects.create(sku='PRD-STOCK-001', name='Produit stock')
        location = InventoryLocation.objects.create(name='Entrepôt stock', code='STOCK-LOC-01')
        StockItem.objects.create(product=product, location=location, quantity=9)

        response = self.client.get(f'/api/products/{product.id}/stock/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['quantity'], 9)
        self.assertEqual(response.data['locations'][0]['location'], location.id)
