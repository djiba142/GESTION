from rest_framework import generics, permissions

from users.permissions import role_permission
from .models import Expense, ExpenseAttachment, ExpenseCategory
from .serializers import ExpenseAttachmentSerializer, ExpenseCategorySerializer, ExpenseSerializer


class ExpenseCategoryListCreateView(generics.ListCreateAPIView):
    queryset = ExpenseCategory.objects.all()
    serializer_class = ExpenseCategorySerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('core')]


class ExpenseListCreateView(generics.ListCreateAPIView):
    queryset = Expense.objects.select_related('category', 'created_by').all()
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('core')]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ExpenseDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Expense.objects.select_related('category', 'created_by').all()
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('core')]


class ExpenseAttachmentListCreateView(generics.ListCreateAPIView):
    queryset = ExpenseAttachment.objects.select_related('expense', 'uploaded_by').all()
    serializer_class = ExpenseAttachmentSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('core')]

    def get_queryset(self):
        return self.queryset.filter(expense_id=self.kwargs['expense_id'])

    def perform_create(self, serializer):
        uploaded_file = self.request.FILES.get('file')
        serializer.save(
            expense_id=self.kwargs['expense_id'],
            original_name=getattr(uploaded_file, 'name', ''),
            uploaded_by=self.request.user,
        )
