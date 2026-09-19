from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from core.models import AppSetting
from notifications.models import Notification
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

    def test_message_history_is_available_and_dispatch_is_not_repeatable(self):
        response = self.client.post(
            '/api/v1/notifications/',
            {
                'sale': self.sale.id,
                'channel': 'whatsapp',
                'event_type': 'payment_received',
                'status': 'pending',
                'message': 'Historique message',
                'recipient_phone': '+224600004000',
            },
            format='json',
        )
        notification_id = response.data['id']
        dispatch_url = f'/api/v1/notifications/{notification_id}/dispatch/'
        self.assertEqual(self.client.post(dispatch_url, format='json').status_code, 200)
        self.assertEqual(self.client.post(dispatch_url, format='json').status_code, 409)

        history = self.client.get('/api/v1/messages/')
        self.assertEqual(history.status_code, 200)
        self.assertTrue(any(item['id'] == notification_id for item in history.data['results']))

    def test_weekly_credit_reminders_are_generated_for_customers_with_open_balance(self):
        customer = Customer.objects.create(full_name='Aminata Koné', phone='+224600005000')
        Sale.objects.create(
            customer=customer,
            status='partial',
            payment_method='credit',
            total_amount='120000.00',
            amount_paid='30000.00',
        )

        response = self.client.post('/api/notifications/reminders/weekly/', format='json')

        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.data['created'], 0)
        self.assertTrue(
            Notification.objects.filter(
                recipient_phone=customer.phone,
                event_type='credit_reminder',
                channel='whatsapp',
            ).exists()
        )

    @patch('notifications.services.requests.post')
    def test_whatsapp_dispatch_uses_configured_provider(self, mock_post):
        AppSetting.objects.create(key='whatsapp_api_endpoint', value='https://example.test/whatsapp')
        AppSetting.objects.create(key='whatsapp_api_key', value='secret-key')
        AppSetting.objects.create(key='whatsapp_sender_id', value='NEXORA')
        notification = Notification.objects.create(
            sale=self.sale,
            channel='whatsapp',
            event_type='payment_received',
            status='pending',
            message='Paiement reçu pour votre commande.',
            recipient_phone='+224600004000',
        )

        mock_post.return_value.status_code = 200
        mock_post.return_value.ok = True
        mock_post.return_value.json.return_value = {'status': 'queued'}

        response = self.client.post(f'/api/notifications/{notification.id}/dispatch/', format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'sent')
        mock_post.assert_called_once()

    def test_message_history_includes_customer_and_export_metadata(self):
        notification = Notification.objects.create(
            sale=self.sale,
            channel='whatsapp',
            event_type='credit_reminder',
            status='pending',
            message='Rappel de paiement',
            recipient_phone='+224600004000',
        )

        history = self.client.get('/api/notifications/history/')

        self.assertEqual(history.status_code, 200)
        self.assertTrue(any(item['id'] == notification.id for item in history.data['results']))
        self.assertIn('customer_name', history.data['results'][0])

    def test_notification_export_csv_is_available(self):
        Notification.objects.create(
            sale=self.sale,
            channel='whatsapp',
            event_type='credit_reminder',
            status='pending',
            message='Rappel facture',
            recipient_phone='+224600004000',
        )

        response = self.client.get('/api/notifications/export/?format=csv')

        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
        self.assertIn('event_type', response.content.decode('utf-8'))
