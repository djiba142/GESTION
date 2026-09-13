from rest_framework import generics, permissions, status
from rest_framework.response import Response

from users.permissions import role_permission
from .models import Document
from .serializers import DocumentSerializer


class DocumentListCreateView(generics.ListCreateAPIView):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('core')]


class DocumentDetailView(generics.RetrieveUpdateAPIView):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated, role_permission('core')]

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.status = 'archived'
        instance.notes = instance.notes or ''
        if 'archivé' not in instance.notes.lower():
            instance.notes = f"{instance.notes} Archivage effectué par {request.user.display_name or request.user.username}.".strip()
        instance.save(update_fields=['status', 'notes', 'updated_at'])
        return Response(self.get_serializer(instance).data, status=status.HTTP_200_OK)
