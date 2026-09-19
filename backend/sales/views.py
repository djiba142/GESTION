from rest_framework import generics, permissions, status
from rest_framework.response import Response

from users.permissions import SensitiveMutationPermission, role_permission
from core.idempotency import replay_idempotent_request, store_idempotent_response
from .models import Sale
from .serializers import SaleSerializer


class SaleListCreateView(generics.ListCreateAPIView):
    queryset = Sale.objects.select_related('customer').prefetch_related('items__product').all()
    serializer_class = SaleSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('sales')]

    def create(self, request, *args, **kwargs):
        endpoint = request.path
        key, replay = replay_idempotent_request(request, endpoint)
        if replay is not None:
            return replay
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        response = Response(serializer.data, status=status.HTTP_201_CREATED)
        store_idempotent_response(request, endpoint, key, response)
        return response


class SaleDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Sale.objects.select_related('customer').prefetch_related('items__product').all()
    serializer_class = SaleSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('sales'), SensitiveMutationPermission]

    def destroy(self, request, *args, **kwargs):
        return Response(
            {'detail': 'La suppression physique d’une vente est interdite.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class ExternalSaleListCreateView(SaleListCreateView):
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data['is_external'] = True
        endpoint = request.path
        key, replay = replay_idempotent_request(request, endpoint)
        if replay is not None:
            return replay
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        response = Response(serializer.data, status=status.HTTP_201_CREATED)
        store_idempotent_response(request, endpoint, key, response)
        return response
