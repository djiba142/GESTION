from django.urls import path

from .views import InvoiceDetailView, InvoiceListView

urlpatterns = [
    path('', InvoiceListView.as_view(), name='invoice-list'),
    path('<int:pk>/', InvoiceDetailView.as_view(), name='invoice-detail'),
]
