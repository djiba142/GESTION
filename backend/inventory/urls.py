from django.urls import path

from .views import (
    CartonDetailView,
    CartonQrView,
    CartonListCreateView,
    InventoryLocationDetailView,
    InventoryLocationListCreateView,
    InventoryLocationStockView,
    StockItemListView,
    StockMovementDetailView,
    StockMovementListCreateView,
    StockTransferActionView,
    StockTransferDetailView,
    StockTransferListCreateView,
)

urlpatterns = [
    path('locations/', InventoryLocationListCreateView.as_view(), name='inventory-location-list-create'),
    path('locations/<int:pk>/', InventoryLocationDetailView.as_view(), name='inventory-location-detail'),
    path('stock/', StockItemListView.as_view(), name='stock-item-list'),
    path('locations/<int:pk>/stock/', InventoryLocationStockView.as_view(), name='location-stock'),
    path('movements/', StockMovementListCreateView.as_view(), name='stock-movement-list-create'),
    path('movements/<int:pk>/', StockMovementDetailView.as_view(), name='stock-movement-detail'),
    path('transfers/', StockTransferListCreateView.as_view(), name='stock-transfer-list-create'),
    path('transfers/<int:pk>/', StockTransferDetailView.as_view(), name='stock-transfer-detail'),
    path('transfers/<int:pk>/<str:action>/', StockTransferActionView.as_view(), name='stock-transfer-action'),
    path('cartons/', CartonListCreateView.as_view(), name='carton-list-create'),
    path('cartons/<int:pk>/', CartonDetailView.as_view(), name='carton-detail'),
    path('cartons/<int:pk>/qr/', CartonQrView.as_view(), name='carton-qr'),
]
