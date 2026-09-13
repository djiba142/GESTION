from django.core.exceptions import ValidationError
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from users.permissions import SensitiveMutationPermission, role_permission
from .models import Carton, InventoryLocation, StockItem, StockMovement, StockTransfer
from .serializers import CartonSerializer, InventoryLocationSerializer, StockItemSerializer, StockMovementSerializer, StockTransferSerializer


class InventoryLocationListCreateView(generics.ListCreateAPIView):
    queryset = InventoryLocation.objects.all()
    serializer_class = InventoryLocationSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('inventory')]


class InventoryLocationDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = InventoryLocation.objects.all()
    serializer_class = InventoryLocationSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('inventory'), SensitiveMutationPermission]


class StockItemListView(generics.ListAPIView):
    queryset = StockItem.objects.select_related('product', 'location').all()
    serializer_class = StockItemSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('inventory')]


class StockMovementListCreateView(generics.ListCreateAPIView):
    queryset = StockMovement.objects.select_related('product', 'location', 'created_by').all()
    serializer_class = StockMovementSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('inventory')]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            self.perform_create(serializer)
        except ValidationError as exc:
            return Response({'quantity': [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class StockMovementDetailView(generics.RetrieveAPIView):
    queryset = StockMovement.objects.select_related('product', 'location', 'created_by').all()
    serializer_class = StockMovementSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('inventory')]


class StockTransferListCreateView(generics.ListCreateAPIView):
    queryset = StockTransfer.objects.select_related('product', 'from_location', 'to_location', 'created_by').all()
    serializer_class = StockTransferSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('inventory')]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        try:
            self.perform_create(serializer)
        except ValidationError as exc:
            return Response({'quantity': [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class StockTransferDetailView(generics.RetrieveAPIView):
    queryset = StockTransfer.objects.select_related('product', 'from_location', 'to_location', 'created_by').all()
    serializer_class = StockTransferSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('inventory')]


class CartonListCreateView(generics.ListCreateAPIView):
    queryset = Carton.objects.select_related('product', 'location').all()
    serializer_class = CartonSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('inventory')]


class CartonDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Carton.objects.select_related('product', 'location').all()
    serializer_class = CartonSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('inventory'), SensitiveMutationPermission]
