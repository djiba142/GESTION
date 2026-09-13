from rest_framework import generics, permissions

from users.permissions import role_permission
from .models import Expense, ExpenseCategory
from .serializers import ExpenseCategorySerializer, ExpenseSerializer


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
