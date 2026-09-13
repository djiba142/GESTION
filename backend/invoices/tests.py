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
