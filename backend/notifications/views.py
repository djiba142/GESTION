from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from users.permissions import role_permission
from .models import Notification
from .serializers import NotificationSerializer


class NotificationListCreateView(generics.ListCreateAPIView):
    queryset = Notification.objects.select_related('sale').all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('notifications')]


class NotificationDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Notification.objects.select_related('sale').all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('notifications')]


class NotificationReadView(generics.GenericAPIView):
    queryset = Notification.objects.select_related('sale').all()
    permission_classes = [permissions.IsAuthenticated, role_permission('notifications')]

    def post(self, request, *args, **kwargs):
        notification = self.get_object()
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=['is_read', 'read_at', 'updated_at'])
        serializer = NotificationSerializer(notification)
        return Response(serializer.data, status=status.HTTP_200_OK)


class NotificationDispatchView(generics.GenericAPIView):
    queryset = Notification.objects.select_related('sale').all()
    permission_classes = [permissions.IsAuthenticated, role_permission('notifications')]

    def post(self, request, *args, **kwargs):
        notification = self.get_object()
        notification.status = 'sent'
        notification.is_read = False
        notification.save(update_fields=['status', 'is_read', 'updated_at'])
        serializer = NotificationSerializer(notification)
        return Response(serializer.data, status=status.HTTP_200_OK)
