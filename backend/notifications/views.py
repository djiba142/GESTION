import csv
import io

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import generics, permissions, status, views
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from core.pagination import VersionedApiPagination
from sales.models import Sale
from users.permissions import role_permission
from .models import Notification
from .serializers import NotificationSerializer
from .services import dispatch_whatsapp_notification


class WeeklyCreditReminderView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, role_permission('notifications')]

    def post(self, request, *args, **kwargs):
        created = 0
        open_credit_sales = Sale.objects.filter(payment_method='credit').select_related('customer')

        for sale in open_credit_sales.order_by('customer_id', '-sale_date'):
            remaining = sale.total_amount - sale.amount_paid
            if remaining <= 0:
                continue

            customer = sale.customer
            if not customer.phone:
                continue

            if Notification.objects.filter(
                sale=sale,
                event_type='credit_reminder',
                channel='whatsapp',
                recipient_phone=customer.phone,
            ).exists():
                continue

            message = (
                f"Bonjour {customer.full_name}, votre solde restant sur la vente #{sale.id} "
                f"est de {remaining:.2f} FCFA. Merci de régulariser votre paiement."
            )
            Notification.objects.create(
                sale=sale,
                channel='whatsapp',
                event_type='credit_reminder',
                status='pending',
                message=message,
                recipient_phone=customer.phone,
            )
            created += 1

        return Response({'created': created, 'generated_at': timezone.now()}, status=status.HTTP_200_OK)


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
    serializer_class = NotificationSerializer
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
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('notifications')]

    def post(self, request, *args, **kwargs):
        notification = self.get_object()
        if notification.status == 'sent':
            return Response(
                {'detail': 'Cette notification a déjà été envoyée.'},
                status=status.HTTP_409_CONFLICT,
            )

        if notification.channel == 'whatsapp':
            result = dispatch_whatsapp_notification(notification)
            if not result.get('success', False):
                notification.status = 'failed'
                notification.is_read = False
                notification.save(update_fields=['status', 'is_read', 'updated_at'])
                return Response(
                    {'detail': result.get('error', 'Échec de l’envoi WhatsApp.')},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

        notification.status = 'sent'
        notification.is_read = False
        notification.save(update_fields=['status', 'is_read', 'updated_at'])
        serializer = NotificationSerializer(notification)
        return Response(serializer.data, status=status.HTTP_200_OK)


class NotificationHistoryView(generics.ListAPIView):
    queryset = Notification.objects.select_related('sale__customer').all()
    serializer_class = NotificationSerializer
    pagination_class = VersionedApiPagination
    permission_classes = [permissions.IsAuthenticated, role_permission('notifications')]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset()).order_by('-created_at')
        page = self.paginate_queryset(queryset)
        items = []
        for notification in page or queryset:
            payload = NotificationSerializer(notification).data
            customer = notification.sale.customer if notification.sale else None
            payload['customer_name'] = customer.full_name if customer else ''
            payload['customer_phone'] = customer.phone if customer else ''
            payload['sale_id'] = notification.sale_id
            payload['sale_total'] = str(notification.sale.total_amount) if notification.sale else ''
            payload['sale_status'] = notification.sale.status if notification.sale else ''
            items.append(payload)

        if page is not None:
            return self.get_paginated_response(items)
        return Response(items, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, role_permission('notifications')])
def NotificationExportView(request, *args, **kwargs):
    notifications = Notification.objects.select_related('sale__customer').order_by('-created_at')
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow([
        'id', 'event_type', 'channel', 'status', 'recipient_phone', 'customer_name',
        'sale_id', 'sale_total', 'sale_status', 'message', 'created_at'
    ])
    for notification in notifications:
        customer = notification.sale.customer if notification.sale else None
        writer.writerow([
            notification.id,
            notification.event_type,
            notification.channel,
            notification.status,
            notification.recipient_phone,
            customer.full_name if customer else '',
            notification.sale_id or '',
            notification.sale.total_amount if notification.sale else '',
            notification.sale.status if notification.sale else '',
            notification.message,
            notification.created_at.isoformat() if notification.created_at else '',
        ])

    response = HttpResponse(csv_buffer.getvalue(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="notifications.csv"'
    return response


class MessageHistoryView(generics.ListAPIView):
    queryset = Notification.objects.select_related('sale').all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('notifications')]
