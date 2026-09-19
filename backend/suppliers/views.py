import csv
import io
import re

import pandas as pd
from django.db import transaction
from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from products.models import Product
from purchases.models import PurchaseOrder, PurchaseOrderItem
from users.permissions import role_permission
from .models import ExchangeRate, Supplier, SupplierImport, SupplierImportRow
from .serializers import ExchangeRateSerializer, SupplierImportRequestSerializer, SupplierImportSerializer, SupplierSerializer


FIELD_ALIASES = {
    'reference': [
        'reference', 'supplier_reference', 'supplierreference', 'product_code', 'productcode', 'code', 'sku', 'ref',
        'article', 'article_code', 'articlecode', 'reference_fournisseur', 'referencefournisseur'
    ],
    'name': [
        'name', 'product', 'description', 'designation', 'product_name', 'productname', 'item_name', 'itemname', 'title',
        'produit', 'designation_produit', 'description_produit'
    ],
    'quantity': ['quantity', 'qty', 'qte', 'quantite', 'count'],
    'unit_price': ['unit_price', 'unitprice', 'price', 'prix', 'prix_unitaire', 'unitcost', 'unit_cost'],
    'currency': ['currency', 'devise', 'monnaie'],
    'brand': ['brand', 'marque'],
    'image': ['image', 'image_url', 'imageurl', 'photo', 'picture'],
}


def _normalize_header(value):
    return re.sub(r'[^a-z0-9]+', '', str(value or '').lower())


def _scalar_from_row(row, aliases):
    for alias in aliases:
        normalized_alias = _normalize_header(alias)
        for key, value in row.items():
            if _normalize_header(key) == normalized_alias:
                if value is None:
                    return ''
                return str(value).strip()
    return ''


def _parse_quantity(value):
    if value in (None, ''):
        return 0
    try:
        return int(float(str(value).replace(',', '.')))
    except (TypeError, ValueError):
        return 0


def _parse_price(value):
    if value in (None, ''):
        return 0.0
    cleaned = str(value).strip().replace(' ', '').replace('€', '').replace('$', '').replace('GNF', '')
    cleaned = cleaned.replace('.', '').replace(',', '.') if cleaned.count(',') == 1 and '.' not in cleaned else cleaned
    if cleaned.endswith('%'):
        cleaned = cleaned[:-1]
    try:
        return float(cleaned)
    except (TypeError, ValueError):
        return 0.0


def _extract_rows_from_uploaded_file(file_obj):
    file_obj.seek(0)
    file_name = getattr(file_obj, 'name', '').lower()
    file_bytes = file_obj.read()

    if file_name.endswith('.csv'):
        content = file_bytes.decode('utf-8-sig', errors='replace')
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
    else:
        try:
            dataframe = pd.read_excel(io.BytesIO(file_bytes), engine='openpyxl')
        except Exception:
            dataframe = pd.read_excel(io.BytesIO(file_bytes))
        rows = dataframe.where(pd.notna(dataframe), None).to_dict(orient='records')

    parsed_rows = []
    for row in rows:
        if not row:
            continue
        reference = _scalar_from_row(row, FIELD_ALIASES['reference']) or _scalar_from_row(row, ['reference_fournisseur'])
        name = _scalar_from_row(row, FIELD_ALIASES['name']) or _scalar_from_row(row, ['produit', 'description'])
        quantity = _parse_quantity(_scalar_from_row(row, FIELD_ALIASES['quantity']))
        unit_price = _parse_price(_scalar_from_row(row, FIELD_ALIASES['unit_price']))
        currency = (_scalar_from_row(row, FIELD_ALIASES['currency']) or 'USD').upper()

        if not reference and not name:
            continue

        parsed_rows.append({
            'reference': reference,
            'name': name,
            'quantity': quantity,
            'unit_price': unit_price,
            'currency': currency,
            'matched_product': name,
            'notes': 'Importé depuis fichier fournisseur',
        })

    return parsed_rows


class SupplierListCreateView(generics.ListCreateAPIView):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('suppliers')]
    pagination_class = None

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

    @extend_schema(request=SupplierImportRequestSerializer, responses={201: SupplierImportSerializer})
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

        allowed_extensions = ('.csv', '.xlsx', '.xls')
        file_name = getattr(file_obj, 'name', '').lower()
        if not file_name.endswith(allowed_extensions):
            return Response({'file': ['Seuls les fichiers CSV, XLSX et XLS sont acceptés.']}, status=status.HTTP_400_BAD_REQUEST)
        if file_obj.size > 10 * 1024 * 1024:
            return Response({'file': ['La taille maximale du fichier est de 10 Mo.']}, status=status.HTTP_400_BAD_REQUEST)

        rows = _extract_rows_from_uploaded_file(file_obj)

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


class SupplierImportConfirmView(generics.GenericAPIView):
    queryset = SupplierImport.objects.prefetch_related('rows').all()
    serializer_class = SupplierImportSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('suppliers')]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        import_record = self.get_object()
        if import_record.status != 'parsed':
            return Response(
                {'detail': 'Cet import a déjà été traité.'},
                status=status.HTTP_409_CONFLICT,
            )

        order_reference = f"PO-{import_record.supplier.name[:3].upper()}-{import_record.pk:04d}"
        purchase_order = PurchaseOrder.objects.create(
            supplier=import_record.supplier,
            reference=order_reference,
            status='draft',
            notes=f"Commande créée depuis l’import fournisseur {import_record.file_name}",
        )

        for row in import_record.rows.all():
            product_name = (row.name or row.matched_product or 'Produit importé').strip() or 'Produit importé'
            reference = (row.reference or '').strip()
            product = None
            if reference:
                product = Product.objects.filter(sku__iexact=reference).first()
            if product is None:
                product = Product.objects.filter(name__iexact=product_name).first()
            if product is None:
                product = Product.objects.create(
                    sku=reference or f"IMP-{import_record.pk}-{row.id:04d}",
                    name=product_name,
                    purchase_price=row.unit_price,
                    cost_price=row.unit_price,
                    selling_price=row.unit_price,
                    currency=(row.currency or 'USD').upper(),
                    quantity=0,
                    alert_threshold=0,
                    description=f"Produit créé depuis import fournisseur: {import_record.file_name}",
                )

            PurchaseOrderItem.objects.create(
                purchase_order=purchase_order,
                product=product,
                quantity=row.quantity or 1,
                unit_cost=row.unit_price or 0,
            )

        import_record.status = 'validated'
        import_record.purchase_order = purchase_order
        import_record.save(update_fields=['status', 'purchase_order'])

        payload = self.get_serializer(import_record).data
        return Response(payload, status=status.HTTP_200_OK)
