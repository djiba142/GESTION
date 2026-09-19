from django.urls import path

from .views import PurchaseOrderActionView, PurchaseOrderDetailView, PurchaseOrderListCreateView, PurchaseReceiptDetailView, PurchaseReceiptListCreateView, PurchaseReceiptValidateView

urlpatterns = [
    path('orders/', PurchaseOrderListCreateView.as_view(), name='purchase-order-list-create'),
    path('orders/<int:pk>/', PurchaseOrderDetailView.as_view(), name='purchase-order-detail'),
    path('orders/<int:pk>/<str:action>/', PurchaseOrderActionView.as_view(), name='purchase-order-action'),
    path('receipts/', PurchaseReceiptListCreateView.as_view(), name='purchase-receipt-list-create'),
    path('receipts/<int:pk>/', PurchaseReceiptDetailView.as_view(), name='purchase-receipt-detail'),
    path('receipts/<int:pk>/validate/', PurchaseReceiptValidateView.as_view(), name='purchase-receipt-validate'),
]
