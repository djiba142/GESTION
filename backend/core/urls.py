from django.urls import path

from .views import (
    AdvancedReportingView,
    AppSettingDetailView,
    AppSettingListCreateView,
    AuditLogListView,
    CashflowSummaryView,
    DashboardSummaryView,
    GlobalSearchView,
)

urlpatterns = [
    path('audit/', AuditLogListView.as_view(), name='audit-log-list'),
    path('dashboard/', DashboardSummaryView.as_view(), name='dashboard-summary'),
    path('cashflow/', CashflowSummaryView.as_view(), name='cashflow-summary'),
    path('reports/', AdvancedReportingView.as_view(), name='advanced-reporting'),
    path('search/', GlobalSearchView.as_view(), name='global-search'),
    path('settings/', AppSettingListCreateView.as_view(), name='app-setting-list-create'),
    path('settings/<int:pk>/', AppSettingDetailView.as_view(), name='app-setting-detail'),
]
