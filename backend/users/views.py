from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.utils import timezone
from django.utils.translation import activate, get_language
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiTypes, extend_schema, extend_schema_view

from core.models import AuditLog
from .models import User
from .permissions import IsAdminUser
from .serializers import LoginSerializer, LogoutResponseSerializer, PinResetConfirmSerializer, PinResetRequestSerializer, RegisterSerializer, UserProfileSerializer, UserSerializer


class UserListView(generics.ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        AuditLog.objects.create(
            user=request.user,
            action='create',
            model_name='User',
            record_id=user.id,
            details=f"Utilisateur créé: {user.display_name}",
        )
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        AuditLog.objects.create(
            user=request.user,
            action='update',
            model_name='User',
            record_id=user.id,
            details=f"Utilisateur mis à jour: {user.display_name}",
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        return Response(
            {'detail': 'La suppression physique d’un utilisateur est interdite. Utilisez la désactivation.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class UserMeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        new_language = serializer.validated_data.get('preferred_language', instance.preferred_language)
        new_keyboard = serializer.validated_data.get('keyboard_layout', instance.keyboard_layout)

        instance = serializer.save()
        instance.preferred_language = new_language
        instance.keyboard_layout = new_keyboard
        instance.save(update_fields=['preferred_language', 'keyboard_layout'])

        request.session['django_language'] = new_language
        request.session['keyboard_layout'] = new_keyboard
        activate(new_language)
        if hasattr(request, 'user'):
            request.user = instance

        return Response(self.get_serializer(instance).data, status=status.HTTP_200_OK)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(request=LoginSerializer, responses={200: UserSerializer})
    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        identifier = serializer.validated_data['identifier']
        pin = serializer.validated_data['pin']

        user = User.objects.filter(username=identifier).first()
        if user is None:
            user = User.objects.filter(email=identifier).first()
        if user is None:
            user = User.objects.filter(phone=identifier).first()

        if user is None:
            return Response({'success': False, 'message': 'Identifiant introuvable.'}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({'success': False, 'message': 'Compte inactif.'}, status=status.HTTP_401_UNAUTHORIZED)

        if user.locked_until and user.locked_until > timezone.now():
            return Response({'success': False, 'message': 'Compte temporairement bloqué. Réessayez plus tard.'}, status=status.HTTP_403_FORBIDDEN)

        if not user.check_pin(pin):
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= 5:
                user.locked_until = timezone.now() + timezone.timedelta(minutes=15)
                user.failed_login_attempts = 0
                user.save(update_fields=['failed_login_attempts', 'locked_until'])
                return Response({'success': False, 'message': 'Compte bloqué temporairement après 5 échecs de connexion.'}, status=status.HTTP_403_FORBIDDEN)
            user.save(update_fields=['failed_login_attempts'])
            return Response({'success': False, 'message': 'Code PIN incorrect.'}, status=status.HTTP_401_UNAUTHORIZED)

        user.failed_login_attempts = 0
        user.locked_until = None
        user.save(update_fields=['failed_login_attempts', 'locked_until'])

        login(request, user)
        AuditLog.objects.create(
            user=user,
            action='login',
            model_name='User',
            record_id=user.id,
            details=f'Connexion réussie pour {user.display_name}',
        )
        return Response({
            'success': True,
            'message': 'Connexion réussie.',
            'user': UserSerializer(user).data,
        }, status=status.HTTP_200_OK)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            'success': True,
            'message': 'Compte créé avec succès. Vous pouvez vous connecter.',
            'user': UserSerializer(user).data,
        }, status=status.HTTP_201_CREATED)


class PinResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(request=PinResetRequestSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request, *args, **kwargs):
        serializer = PinResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email__iexact=serializer.validated_data['email'], is_active=True).first()
        response_data = {'success': True, 'message': 'Si ce compte existe, les instructions de réinitialisation ont été préparées.'}
        if user and settings.DEBUG:
            response_data['reset_uid'] = user.pk
            response_data['reset_token'] = default_token_generator.make_token(user)
        return Response(response_data, status=status.HTTP_200_OK)


class PinResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(request=PinResetConfirmSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request, *args, **kwargs):
        serializer = PinResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(pk=serializer.validated_data['uid'], is_active=True).first()
        if not user or not default_token_generator.check_token(user, serializer.validated_data['token']):
            return Response({'success': False, 'message': 'Le lien de réinitialisation est invalide ou expiré.'}, status=status.HTTP_400_BAD_REQUEST)
        user.set_pin(serializer.validated_data['pin'])
        user.failed_login_attempts = 0
        user.locked_until = None
        user.save(update_fields=['pin_code', 'failed_login_attempts', 'locked_until', 'updated_at'])
        return Response({'success': True, 'message': 'Code PIN réinitialisé. Vous pouvez vous connecter.'}, status=status.HTTP_200_OK)


@extend_schema_view(post=extend_schema(responses=LogoutResponseSerializer))
class LogoutView(APIView):
    serializer_class = LogoutResponseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        logout(request)
        return Response({'success': True, 'message': 'Déconnexion réussie.'}, status=status.HTTP_200_OK)
