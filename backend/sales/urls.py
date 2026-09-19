from django.urls import path

from .views import ExternalSaleListCreateView, SaleDetailView, SaleListCreateView

urlpatterns = [
    path('external/', ExternalSaleListCreateView.as_view(), name='external-sale-list-create'),
    path('', SaleListCreateView.as_view(), name='sale-list-create'),
    path('<int:pk>/', SaleDetailView.as_view(), name='sale-detail'),
]
