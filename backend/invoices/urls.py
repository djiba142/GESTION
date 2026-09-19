from django.urls import path

from .views import InvoiceDetailView, InvoiceListView, InvoicePdfView, InvoiceQrImageView, InvoiceQrView, InvoiceVerifyView

urlpatterns = [
    path('', InvoiceListView.as_view(), name='invoice-list'),
    path('<int:pk>/', InvoiceDetailView.as_view(), name='invoice-detail'),
    path('<int:pk>/pdf/', InvoicePdfView.as_view(), name='invoice-pdf'),
    path('<int:pk>/qr/', InvoiceQrView.as_view(), name='invoice-qr'),
    path('<int:pk>/qr-image/', InvoiceQrImageView.as_view(), name='invoice-qr-image'),
    path('verify/<uuid:token>/', InvoiceVerifyView.as_view(), name='invoice-verify'),
]
