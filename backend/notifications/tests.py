from django.test import TestCase
from rest_framework.test import APIClient

from sales.models import Sale
from users.models import User
from customers.models import Customer


class NotificationApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='notif_admin',
            password='secret123',
            pin_code='1234',
            role='admin',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.customer = Customer.objects.create(full_name='Moussa Bah', phone='+224600004000')
        self.sale = Sale.objects.create(
            customer=self.customer,
            status='paid',
            payment_method='cash',
            total_amount='150000.00',
            amount_paid='150000.00',
        )

    def test_create_notification_record(self):
        response = self.client.post(
            '/api/notifications/',
            {
                'sale': self.sale.id,
                'channel': 'whatsapp',
                'event_type': 'sale_confirmed',
                'status': 'pending',
                'message': 'Votre vente a été confirmée',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['event_type'], 'sale_confirmed')

    def test_notification_status_can_be_updated(self):
        response = self.client.post(
            '/api/notifications/',
            {
                'sale': self.sale.id,
                'channel': 'whatsapp',
                'event_type': 'payment_received',
                'status': 'sent',
                'message': 'Paiement reçu',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], 'sent')

    def test_notification_can_be_marked_as_read(self):
        response = self.client.post(
            '/api/notifications/',
            {
                'sale': self.sale.id,
                'channel': 'whatsapp',
                'event_type': 'invoice_sent',
                'status': 'sent',
                'message': 'Votre facture vient d’être envoyée',
                'recipient_phone': '+224600004000',
            },
            format='json',
        )
        notification_id = response.data['id']

        read_response = self.client.post(f'/api/notifications/{notification_id}/read/', format='json')

        self.assertEqual(read_response.status_code, 200)
        self.assertTrue(read_response.data['is_read'])
        self.assertIsNotNone(read_response.data['read_at'])

    def test_notification_dispatch_marks_message_as_sent(self):
        response = self.client.post(
            '/api/notifications/',
            {
                'sale': self.sale.id,
                'channel': 'whatsapp',
                'event_type': 'payment_received',
                'status': 'pending',
                'message': 'Paiement reçu pour votre achat.',
                'recipient_phone': '+224600004000',
            },
            format='json',
        )
        notification_id = response.data['id']

        dispatch_response = self.client.post(f'/api/notifications/{notification_id}/dispatch/', format='json')

        self.assertEqual(dispatch_response.status_code, 200)
        self.assertEqual(dispatch_response.data['status'], 'sent')
        self.assertEqual(dispatch_response.data['channel'], 'whatsapp')
