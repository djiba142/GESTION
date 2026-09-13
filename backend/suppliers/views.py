import csv
import io

from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import role_permission
from .models import ExchangeRate, Supplier, SupplierImport, SupplierImportRow
from .serializers import ExchangeRateSerializer, SupplierImportSerializer, SupplierSerializer


class SupplierListCreateView(generics.ListCreateAPIView):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('suppliers')]

    def get_queryset(self):
        queryset = Supplier.objects.all()
        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(contact_name__icontains=search) |
                Q(phone__icontains=search) |
                Q(company_name__icontains=search)
            )
        return queryset


class SupplierDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('suppliers')]


class ExchangeRateListCreateView(generics.ListCreateAPIView):
    queryset = ExchangeRate.objects.all()
    serializer_class = ExchangeRateSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('suppliers')]


class SupplierImportView(APIView):
    permission_classes = [permissions.IsAuthenticated, role_permission('suppliers')]

    def post(self, request, *args, **kwargs):
        supplier_id = request.data.get('supplier') or request.POST.get('supplier')
        file_obj = request.FILES.get('file')

        if not supplier_id:
            return Response({'supplier': ['Le fournisseur est requis.']}, status=status.HTTP_400_BAD_REQUEST)
        if not file_obj:
            return Response({'file': ['Le fichier fournisseur est requis.']}, status=status.HTTP_400_BAD_REQUEST)

        supplier = Supplier.objects.filter(pk=supplier_id).first()
        if supplier is None:
            return Response({'supplier': ['Fournisseur introuvable.']}, status=status.HTTP_404_NOT_FOUND)

        try:
            raw_content = file_obj.read().decode('utf-8-sig')
        except UnicodeDecodeError:
            raw_content = file_obj.read().decode('latin-1')

        reader = csv.DictReader(io.StringIO(raw_content))
        rows = []
        for row in reader:
            if not row:
                continue
            reference = (row.get('reference') or row.get('sku') or row.get('code') or '').strip()
            name = (row.get('name') or row.get('product') or row.get('description') or '').strip()
            quantity_value = row.get('quantity', '0')
            price_value = row.get('unit_price', row.get('price', '0'))
            currency = (row.get('currency') or 'USD').strip().upper()
            try:
                quantity = int(float(quantity_value))
            except (TypeError, ValueError):
                quantity = 0
            try:
                unit_price = float(price_value)
            except (TypeError, ValueError):
                unit_price = 0

            if not reference and not name:
                continue

            rows.append({
                'reference': reference,
                'name': name,
                'quantity': quantity,
                'unit_price': unit_price,
                'currency': currency,
                'matched_product': name,
                'notes': 'Importé depuis fichier fournisseur',
            })

        import_record = SupplierImport.objects.create(
            supplier=supplier,
            file_name=getattr(file_obj, 'name', 'fichier.csv'),
            status='parsed',
            parsed_rows=len(rows),
        )

        for row in rows:
            SupplierImportRow.objects.create(supplier_import=import_record, **row)

        payload = SupplierImportSerializer(import_record).data
        return Response(payload, status=status.HTTP_201_CREATED)
