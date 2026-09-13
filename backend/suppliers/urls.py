from django.urls import path

from .views import ExchangeRateListCreateView, SupplierDetailView, SupplierImportView, SupplierListCreateView

urlpatterns = [
    path('exchange-rates/', ExchangeRateListCreateView.as_view(), name='exchange-rate-list-create'),
    path('imports/', SupplierImportView.as_view(), name='supplier-import-create'),
    path('', SupplierListCreateView.as_view(), name='supplier-list-create'),
    path('<int:pk>/', SupplierDetailView.as_view(), name='supplier-detail'),
]
