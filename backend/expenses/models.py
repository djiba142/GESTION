from django.conf import settings
from django.db import models


class ExpenseCategory(models.Model):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Expense(models.Model):
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT, related_name='expenses')
    title = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    expense_date = models.DateTimeField(auto_now_add=True)
    beneficiary = models.CharField(max_length=200, blank=True, default='')
    reference = models.CharField(max_length=120, blank=True, default='')
    justification = models.TextField(blank=True, default='')
    notes = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-expense_date']

    def __str__(self):
        return f'{self.title} - {self.amount}'


class ExpenseAttachment(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='expense_justifications/')
    original_name = models.CharField(max_length=255, blank=True, default='')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']
