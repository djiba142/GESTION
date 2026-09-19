from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from customers.models import Customer
from products.models import Product
from sales.models import Sale
from users.models import User


class InvoiceApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='invoice_manager',
            password='secret123',
            pin_code='1234',
            role='manager',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.customer = Customer.objects.create(full_name='Aly Diallo', phone='+224600010001')
        self.product = Product.objects.create(
            sku='INV-001',
            name='Produit facture',
            brand='NEXORA',
            purchase_price='25000',
            selling_price='40000',
            quantity=5,
            alert_threshold=1,
        )

    def test_invoice_list_endpoint_exposes_invoice_data(self):
        from sales.models import Invoice

        sale = Sale.objects.create(
            customer=self.customer,
            status='paid',
            payment_method='cash',
            total_amount=Decimal('40000.00'),
            amount_paid=Decimal('40000.00'),
        )
        sale.items.create(product=self.product, quantity=1, unit_price=Decimal('40000.00'))

        invoice = Invoice.objects.create(
            sale=sale,
            invoice_number='INV-TEST-0001',
            total_amount=sale.total_amount,
            paid_amount=sale.amount_paid,
        )
        invoice.generate_qr_code()
        invoice.save(update_fields=['qr_code'])

        response = self.client.get('/api/invoices/')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.data) >= 1)
        self.assertTrue(any(item['invoice_number'] == invoice.invoice_number for item in response.data))

    def test_invoice_pdf_and_qr_endpoints(self):
        from sales.models import Invoice

        sale = Sale.objects.create(
            customer=self.customer,
            status='paid',
            payment_method='cash',
            total_amount=Decimal('40000.00'),
            amount_paid=Decimal('40000.00'),
        )
        invoice = Invoice.objects.create(
            sale=sale,
            invoice_number='INV-PDF-0001',
            total_amount=sale.total_amount,
            paid_amount=sale.amount_paid,
        )

        pdf_response = self.client.get(f'/api/v1/invoices/{invoice.id}/pdf/')
        qr_response = self.client.get(f'/api/v1/invoices/{invoice.id}/qr/')

        self.assertEqual(pdf_response.status_code, 200)
        self.assertEqual(pdf_response['Content-Type'], 'application/pdf')
        self.assertTrue(pdf_response.content.startswith(b'%PDF-1.4'))
        self.assertEqual(qr_response.status_code, 200)
        self.assertEqual(qr_response.data['qr_code'], invoice.qr_code)

    def test_invoice_verification_token_is_secure_and_publicly_resolvable(self):
        from sales.models import Invoice

        sale = Sale.objects.create(
            customer=self.customer,
            status='paid',
            payment_method='cash',
            total_amount=Decimal('40000.00'),
            amount_paid=Decimal('40000.00'),
        )
        invoice = Invoice.objects.create(
            sale=sale,
            invoice_number='INV-VERIFY-0001',
            total_amount=sale.total_amount,
            paid_amount=sale.amount_paid,
        )

        verify_response = self.client.get(f'/api/invoices/verify/{invoice.verification_token}/')
        qr_image_response = self.client.get(f'/api/invoices/{invoice.id}/qr-image/')

        self.assertEqual(verify_response.status_code, 200)
        self.assertTrue(verify_response.data['valid'])
        self.assertEqual(verify_response.data['invoice_number'], invoice.invoice_number)
        self.assertEqual(qr_image_response.status_code, 200)
        self.assertEqual(qr_image_response['Content-Type'], 'image/png')

    def test_cancelled_invoice_verification_remains_resolvable(self):
        from sales.models import Invoice

        sale = Sale.objects.create(
            customer=self.customer,
            status='cancelled',
            payment_method='cash',
            total_amount=Decimal('40000.00'),
            amount_paid=Decimal('0.00'),
        )
        invoice = Invoice.objects.create(
            sale=sale,
            invoice_number='INV-CANCELLED-0001',
            total_amount=sale.total_amount,
            paid_amount=sale.amount_paid,
        )

        response = self.client.get(f'/api/invoices/verify/{invoice.verification_token}/')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['valid'])
        self.assertEqual(response.data['status'], 'cancelled')
