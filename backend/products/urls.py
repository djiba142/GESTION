from django.urls import path

from .views import CategoryListCreateView, ProductDetailView, ProductLabelView, ProductListCreateView, ProductScanView

urlpatterns = [
    path('categories/', CategoryListCreateView.as_view(), name='category-list-create'),
    path('scan/', ProductScanView.as_view(), name='product-scan'),
    path('<int:pk>/label/', ProductLabelView.as_view(), name='product-label'),
    path('', ProductListCreateView.as_view(), name='product-list-create'),
    path('<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
]
