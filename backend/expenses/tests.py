from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from users.models import User
from .models import Expense, ExpenseCategory


class ExpenseApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='expense_admin',
            password='secret123',
            pin_code='1234',
            role='admin',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.category = ExpenseCategory.objects.create(name='Transport', description='Frais logistique')

    def test_create_expense(self):
        response = self.client.post(
            '/api/expenses/',
            {
                'category': self.category.id,
                'title': 'Transport fournisseur',
                'amount': '540000.00',
                'beneficiary': 'Logistics SARL',
                'reference': 'DEP-001',
                'justification': 'Livraison produit importé',
                'notes': 'Frais de transport international',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Expense.objects.count(), 1)
        self.assertEqual(response.data['title'], 'Transport fournisseur')

    def test_list_expenses(self):
        Expense.objects.create(
            category=self.category,
            title='Entretien véhicule',
            amount='150000.00',
            beneficiary='Garage NEXORA',
            reference='DEP-002',
            created_by=self.user,
        )

        response = self.client.get('/api/expenses/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(item['title'] == 'Entretien véhicule' for item in response.data))

    def test_expense_justification_attachment_upload(self):
        expense = Expense.objects.create(
            category=self.category,
            title='Dépense avec justificatif',
            amount='25000.00',
            created_by=self.user,
        )
        attachment = SimpleUploadedFile('facture.txt', b'justificatif', content_type='text/plain')

        response = self.client.post(
            f'/api/v1/expenses/{expense.id}/attachments/',
            {'file': attachment},
            format='multipart',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['original_name'], 'facture.txt')
