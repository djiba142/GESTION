from io import BytesIO

import qrcode
from django.conf import settings
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from sales.models import Invoice
from users.permissions import role_permission

from .serializers import InvoiceSerializer, invoice_verification_url


def verification_payload(invoice):
    return {
        'valid': invoice.sale.status != 'cancelled',
        'status': 'cancelled' if invoice.sale.status == 'cancelled' else 'validated',
        'invoice_number': invoice.invoice_number,
        'issue_date': invoice.issue_date,
        'total_amount': invoice.total_amount,
        'currency': 'GNF',
        'verification_url': invoice_verification_url(invoice),
    }


class InvoiceListView(generics.ListAPIView):
    queryset = Invoice.objects.select_related('sale__customer').all()
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('sales')]


class InvoiceDetailView(generics.RetrieveAPIView):
    queryset = Invoice.objects.select_related('sale__customer').all()
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('sales')]


class InvoiceQrView(generics.GenericAPIView):
    queryset = Invoice.objects.select_related('sale__customer').all()
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('sales')]

    def get(self, request, *args, **kwargs):
        invoice = self.get_object()
        return Response({
            'type': 'invoice',
            'id': invoice.id,
            'invoice_number': invoice.invoice_number,
            'qr_code': invoice.qr_code,
            'verification_url': invoice_verification_url(invoice),
        }, status=status.HTTP_200_OK)


class InvoiceQrImageView(generics.GenericAPIView):
    queryset = Invoice.objects.select_related('sale__customer').all()
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        invoice = self.get_object()
        qr = qrcode.make(invoice_verification_url(invoice))
        buffer = BytesIO()
        qr.save(buffer, format='PNG')
        return HttpResponse(buffer.getvalue(), content_type='image/png')


class InvoiceVerifyView(generics.GenericAPIView):
    queryset = Invoice.objects.select_related('sale__customer').all()
    permission_classes = [permissions.AllowAny]

    def get(self, request, token, *args, **kwargs):
        invoice = self.get_queryset().filter(verification_token=token).first()
        if invoice is None:
            return Response({'detail': 'Facture introuvable ou jeton invalide.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(verification_payload(invoice), status=status.HTTP_200_OK)


class InvoicePdfView(generics.GenericAPIView):
    queryset = Invoice.objects.select_related('sale__customer').all()
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('sales')]

    def get(self, request, *args, **kwargs):
        invoice = self.get_object()
        buffer = BytesIO()
        document = canvas.Canvas(buffer, pagesize=A4, pdfVersion=(1, 4))
        width, height = A4
        document.setTitle(f'Facture {invoice.invoice_number}')
        document.setFont('Helvetica-Bold', 16)
        document.drawString(72, height - 72, f'Facture {invoice.invoice_number}')
        document.setFont('Helvetica', 11)
        document.drawString(72, height - 104, f'Client : {invoice.sale.customer.full_name}')
        document.drawString(72, height - 128, f'Date : {invoice.issue_date.strftime("%d/%m/%Y")}')
        document.drawString(72, height - 152, f'Total : {invoice.total_amount} GNF')
        document.drawString(72, height - 176, f'Statut : {"ANNULEE" if invoice.sale.status == "cancelled" else "VALIDEE"}')

        qr = qrcode.make(invoice_verification_url(invoice))
        qr_buffer = BytesIO()
        qr.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)
        qr_size = 96
        qr_x = width - 72 - qr_size
        qr_y = 64
        document.drawImage(ImageReader(qr_buffer), qr_x, qr_y, width=qr_size, height=qr_size)
        document.setFont('Helvetica', 8)
        document.drawCentredString(qr_x + qr_size / 2, qr_y - 14, 'Scanner pour verifier la facture')
        document.showPage()
        document.save()
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{invoice.invoice_number}.pdf"'
        return response
