from django.urls import path

from .views import PurchaseOrderDetailView, PurchaseOrderListCreateView, PurchaseReceiptDetailView, PurchaseReceiptListCreateView

urlpatterns = [
    path('orders/', PurchaseOrderListCreateView.as_view(), name='purchase-order-list-create'),
    path('orders/<int:pk>/', PurchaseOrderDetailView.as_view(), name='purchase-order-detail'),
    path('receipts/', PurchaseReceiptListCreateView.as_view(), name='purchase-receipt-list-create'),
    path('receipts/<int:pk>/', PurchaseReceiptDetailView.as_view(), name='purchase-receipt-detail'),
]
