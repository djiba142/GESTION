from django.test import TestCase
from rest_framework.test import APIClient

from .models import Document
from users.models import User


class DocumentApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='doc_admin',
            password='secret123',
            pin_code='1234',
            role='admin',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_document_record(self):
        response = self.client.post(
            '/api/documents/',
            {
                'title': 'Facture fournisseur',
                'document_type': 'invoice',
                'file_name': 'facture-001.pdf',
                'file_url': 'https://example.com/files/facture-001.pdf',
                'related_model': 'purchase',
                'related_id': 12,
                'status': 'active',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['title'], 'Facture fournisseur')

    def test_list_documents(self):
        self.client.post(
            '/api/documents/',
            {
                'title': 'Bon de réception',
                'document_type': 'receipt',
                'file_name': 'bon-01.pdf',
                'file_url': 'https://example.com/files/bon-01.pdf',
                'related_model': 'purchase',
                'related_id': 3,
                'status': 'active',
            },
            format='json',
        )

        response = self.client.get('/api/documents/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(item['title'] == 'Bon de réception' for item in response.data))

    def test_archive_document_instead_of_hard_delete(self):
        response = self.client.post(
            '/api/documents/',
            {
                'title': 'Facture à archiver',
                'document_type': 'invoice',
                'file_name': 'facture-archive.pdf',
                'file_url': 'https://example.com/files/facture-archive.pdf',
                'related_model': 'sale',
                'related_id': 9,
                'status': 'active',
            },
            format='json',
        )
        document_id = response.data['id']

        delete_response = self.client.delete(f'/api/documents/{document_id}/')

        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(delete_response.data['status'], 'archived')
        self.assertTrue(Document.objects.filter(pk=document_id, status='archived').exists())
