from django.urls import path

from .views import (
    AdvancedReportingView,
    AppSettingDetailView,
    AppSettingListCreateView,
    AuditLogListView,
    CashTransactionsView,
    CashView,
    CashflowSummaryView,
    CompanyView,
    DashboardSummaryView,
    FinancialSummaryView,
    GlobalSearchView,
)

urlpatterns = [
    path('company/', CompanyView.as_view(), name='company'),
    path('audit/', AuditLogListView.as_view(), name='audit-log-list'),
    path('dashboard/', DashboardSummaryView.as_view(), name='dashboard-summary'),
    path('cashflow/', CashflowSummaryView.as_view(), name='cashflow-summary'),
    path('cash/', CashView.as_view(), name='cash-summary'),
    path('cash/transactions/', CashTransactionsView.as_view(), name='cash-transactions'),
    path('financial-summary/', FinancialSummaryView.as_view(), name='financial-summary'),
    path('reports/', AdvancedReportingView.as_view(), name='advanced-reporting'),
    path('reports/sales/', AdvancedReportingView.as_view(), name='sales-report'),
    path('reports/inventory/', AdvancedReportingView.as_view(), name='inventory-report'),
    path('reports/credits/', AdvancedReportingView.as_view(), name='credit-report'),
    path('reports/purchases/', AdvancedReportingView.as_view(), name='purchase-report'),
    path('reports/finance/', AdvancedReportingView.as_view(), name='finance-report'),
    path('search/', GlobalSearchView.as_view(), name='global-search'),
    path('settings/', AppSettingListCreateView.as_view(), name='app-setting-list-create'),
    path('settings/<int:pk>/', AppSettingDetailView.as_view(), name='app-setting-detail'),
]
