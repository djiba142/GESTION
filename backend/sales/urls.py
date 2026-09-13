from django.urls import path

from .views import SaleDetailView, SaleListCreateView

urlpatterns = [
    path('', SaleListCreateView.as_view(), name='sale-list-create'),
    path('<int:pk>/', SaleDetailView.as_view(), name='sale-detail'),
]
