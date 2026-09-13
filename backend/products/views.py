from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from users.permissions import SensitiveMutationPermission, role_permission
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer


class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('products')]


class ProductListCreateView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('products')]

    def get_queryset(self):
        queryset = Product.objects.select_related('category').all()
        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(sku__icontains=search) |
                Q(brand__icontains=search) |
                Q(barcode__icontains=search) |
                Q(qr_code__icontains=search)
            )
        return queryset


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('products'), SensitiveMutationPermission]


class ProductLabelView(generics.GenericAPIView):
    queryset = Product.objects.all()
    permission_classes = [permissions.IsAuthenticated, role_permission('products')]

    def post(self, request, *args, **kwargs):
        product = self.get_object()
        product.qr_code = product.generate_qr_code()
        product.save(update_fields=['qr_code'])

        payload = {
            'id': product.id,
            'sku': product.sku,
            'name': product.name,
            'brand': product.brand,
            'barcode': product.barcode,
            'qr_code': product.qr_code,
            'quantity': product.quantity,
            'selling_price': str(product.selling_price),
            'currency': product.currency,
            'unit': product.unit,
            'is_active': product.is_active,
        }
        return Response(payload, status=status.HTTP_200_OK)


class ProductScanView(generics.GenericAPIView):
    queryset = Product.objects.all()
    permission_classes = [permissions.IsAuthenticated, role_permission('products')]

    def get(self, request, *args, **kwargs):
        code = (request.query_params.get('code') or '').strip()
        if not code:
            return Response({'code': ['Le code QR ou code-barres est requis.']}, status=status.HTTP_400_BAD_REQUEST)

        product = Product.objects.filter(Q(qr_code=code) | Q(barcode=code) | Q(sku=code)).first()
        if not product:
            return Response({'detail': 'Produit introuvable pour ce code.'}, status=status.HTTP_404_NOT_FOUND)

        payload = {
            'id': product.id,
            'sku': product.sku,
            'name': product.name,
            'brand': product.brand,
            'barcode': product.barcode,
            'qr_code': product.qr_code,
            'quantity': product.quantity,
            'selling_price': str(product.selling_price),
            'currency': product.currency,
            'unit': product.unit,
            'is_active': product.is_active,
        }
        return Response(payload, status=status.HTTP_200_OK)
