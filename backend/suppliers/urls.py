from django.urls import path

from .views import ExchangeRateListCreateView, SupplierDetailView, SupplierImportConfirmView, SupplierImportView, SupplierListCreateView

urlpatterns = [
    path('exchange-rates/', ExchangeRateListCreateView.as_view(), name='exchange-rate-list-create'),
    path('imports/', SupplierImportView.as_view(), name='supplier-import-create'),
    path('imports/<int:pk>/confirm/', SupplierImportConfirmView.as_view(), name='supplier-import-confirm'),
    path('', SupplierListCreateView.as_view(), name='supplier-list-create'),
    path('<int:pk>/', SupplierDetailView.as_view(), name='supplier-detail'),
]
