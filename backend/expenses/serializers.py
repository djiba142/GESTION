from rest_framework import serializers

from .models import Expense, ExpenseAttachment, ExpenseCategory


class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ['id', 'name', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']


class ExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Expense
        fields = [
            'id', 'category', 'category_name', 'title', 'amount', 'expense_date',
            'beneficiary', 'reference', 'justification', 'notes', 'created_by',
            'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'expense_date', 'created_by', 'created_by_name', 'created_at', 'updated_at']

    def get_category_name(self, obj):
        return obj.category.name if obj.category else None

    def get_created_by_name(self, obj):
        return obj.created_by.display_name if obj.created_by else None


class ExpenseAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseAttachment
        fields = ['id', 'expense', 'file', 'original_name', 'uploaded_by', 'uploaded_at']
        read_only_fields = ['id', 'expense', 'original_name', 'uploaded_by', 'uploaded_at']
