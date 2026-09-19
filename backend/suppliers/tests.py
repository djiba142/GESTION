from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from openpyxl import Workbook
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

    def test_import_supplier_supports_common_aliases_and_excel(self):
        supplier = Supplier.objects.create(name='Import Alias Supplier', phone='+224600000500')
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = 'Commande'
        sheet.append(['Product Code', 'Description', 'Qty', 'Unit Price', 'Currency'])
        sheet.append(['SKU-101', 'Filtre Toyota', '12', '4.50', 'USD'])

        buffer = BytesIO()
        workbook.save(buffer)
        excel_file = SimpleUploadedFile(
            'supplier_aliases.xlsx',
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

        response = self.client.post(
            '/api/suppliers/imports/',
            {'file': excel_file, 'supplier': supplier.id},
            format='multipart',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['parsed_rows'], 1)
        self.assertEqual(response.data['rows'][0]['reference'], 'SKU-101')
        self.assertEqual(response.data['rows'][0]['name'], 'Filtre Toyota')
        self.assertEqual(response.data['rows'][0]['currency'], 'USD')

    def test_versioned_purchase_import_can_be_confirmed_once(self):
        supplier = Supplier.objects.create(name='Import API v1')
        csv_file = SimpleUploadedFile(
            'purchase.csv',
            b'reference,name,quantity,unit_price,currency\nSKU-101,Produit API,3,1200,USD',
            content_type='text/csv',
        )

        response = self.client.post(
            '/api/v1/purchase-imports/',
            {'file': csv_file, 'supplier': supplier.id},
            format='multipart',
        )

        self.assertEqual(response.status_code, 201)
        import_id = response.data['id']
        confirmation = self.client.post(f'/api/v1/purchase-imports/{import_id}/confirm/', format='json')
        self.assertEqual(confirmation.status_code, 200)
        self.assertEqual(confirmation.data['status'], 'validated')

        repeated_confirmation = self.client.post(f'/api/v1/purchase-imports/{import_id}/confirm/', format='json')
        self.assertEqual(repeated_confirmation.status_code, 409)

    def test_supplier_import_confirmation_creates_draft_purchase_order(self):
        supplier = Supplier.objects.create(name='Import to Order Supplier', phone='+224600000600')
        csv_file = SimpleUploadedFile(
            'order_import.csv',
            'reference,name,quantity,unit_price,currency\nSKU-PO-1,Produit commande,4,1500,USD'.encode('utf-8'),
            content_type='text/csv',
        )

        response = self.client.post(
            '/api/suppliers/imports/',
            {'file': csv_file, 'supplier': supplier.id},
            format='multipart',
        )

        self.assertEqual(response.status_code, 201)
        confirmation = self.client.post(f"/api/suppliers/imports/{response.data['id']}/confirm/", format='json')
        self.assertEqual(confirmation.status_code, 200)
        self.assertEqual(confirmation.data['status'], 'validated')
        self.assertIn('purchase_order', confirmation.data)
        self.assertEqual(confirmation.data['purchase_order']['status'], 'draft')
        self.assertEqual(confirmation.data['purchase_order']['items'][0]['quantity'], 4)

    def test_supplier_import_rejects_non_csv_files(self):
        supplier = Supplier.objects.create(name='Import validation')
        file_obj = SimpleUploadedFile('purchase.txt', b'not,csv', content_type='text/plain')

        response = self.client.post(
            '/api/v1/purchase-imports/',
            {'file': file_obj, 'supplier': supplier.id},
            format='multipart',
        )

        self.assertEqual(response.status_code, 400)
