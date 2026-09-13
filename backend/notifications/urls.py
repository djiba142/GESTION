from django.urls import path

from .views import (
    NotificationDetailView,
    NotificationDispatchView,
    NotificationListCreateView,
    NotificationReadView,
)

urlpatterns = [
    path('', NotificationListCreateView.as_view(), name='notification-list-create'),
    path('<int:pk>/read/', NotificationReadView.as_view(), name='notification-read'),
    path('<int:pk>/dispatch/', NotificationDispatchView.as_view(), name='notification-dispatch'),
    path('<int:pk>/', NotificationDetailView.as_view(), name='notification-detail'),
]
