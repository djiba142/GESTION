from django.urls import path

from .views import CustomerPaymentSummaryView, PaymentDetailView, PaymentListCreateView

urlpatterns = [
    path('', PaymentListCreateView.as_view(), name='payment-list-create'),
    path('<int:pk>/', PaymentDetailView.as_view(), name='payment-detail'),
    path('customer/<int:customer_id>/', CustomerPaymentSummaryView.as_view(), name='customer-payment-summary'),
]
