from django.urls import path

from .views import CategoryListCreateView, ProductArchiveView, ProductDetailView, ProductLabelView, ProductListCreateView, ProductQrView, ProductScanView, ProductStockView

urlpatterns = [
    path('categories/', CategoryListCreateView.as_view(), name='category-list-create'),
    path('scan/', ProductScanView.as_view(), name='product-scan'),
    path('<int:pk>/stock/', ProductStockView.as_view(), name='product-stock'),
    path('<int:pk>/archive/', ProductArchiveView.as_view(), name='product-archive'),
    path('<int:pk>/qr/', ProductQrView.as_view(), name='product-qr'),
    path('<int:pk>/label/', ProductLabelView.as_view(), name='product-label'),
    path('', ProductListCreateView.as_view(), name='product-list-create'),
    path('<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
]
