from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from users.models import User
from .models import Supplier


class SupplierApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='fournisseur_manager',
            password='secret123',
            pin_code='1234',
            role='manager',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_supplier(self):
        payload = {
            'name': 'SOGEM',
            'contact_name': 'Amadou Diallo',
            'phone': '+224600000100',
            'email': 'contact@sogem.sn',
            'address': 'Conakry',
            'company_name': 'SOGEM SARL',
            'notes': 'Fournisseur principal'
        }
        response = self.client.post('/api/suppliers/', payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Supplier.objects.count(), 1)
        self.assertEqual(response.data['name'], 'SOGEM')

    def test_list_suppliers(self):
        Supplier.objects.create(name='SUP1', phone='+224600000200')
        response = self.client.get('/api/suppliers/')
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 1)

    def test_search_supplier_by_name(self):
        Supplier.objects.create(name='Alpha Distribution', phone='+224600000300')
        response = self.client.get('/api/suppliers/?search=Alpha')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(item['name'] == 'Alpha Distribution' for item in response.data))

    def test_create_exchange_rate(self):
        response = self.client.post(
            '/api/suppliers/exchange-rates/',
            {
                'source_currency': 'USD',
                'target_currency': 'GNF',
                'rate': '9000.00',
                'effective_date': '2026-09-12',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['source_currency'], 'USD')

    def test_import_supplier_csv(self):
        supplier = Supplier.objects.create(name='Import Supplier', phone='+224600000400')
        csv_file = SimpleUploadedFile(
            'supplier_import.csv',
            b'reference,name,quantity,unit_price,currency\nSKU-001,Produit A,10,2500,USD\nSKU-002,Produit B,5,3750,USD',
            content_type='text/csv',
        )

        response = self.client.post(
            '/api/suppliers/imports/',
            {'file': csv_file, 'supplier': supplier.id},
            format='multipart',
        )
        self.assertEqual(response.status_code, 201)
        self.assertGreaterEqual(response.data['parsed_rows'], 2)
