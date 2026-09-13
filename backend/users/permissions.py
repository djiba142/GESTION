from django.conf import settings
from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminUser(BasePermission):
    """Autorise uniquement les administrateurs à accéder à certaines ressources."""

    message = 'Accès réservé aux administrateurs.'

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            getattr(request.user, 'role', None) == 'admin'
        )


class IsManagerOrAdmin(BasePermission):
    """Autorise les gestionnaires et administrateurs pour les actions sensibles."""

    message = 'Cette opération sensible exige un rôle de gestion ou d’administration.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if getattr(request.user, 'is_superuser', False):
            return True
        return getattr(request.user, 'role', None) in {'admin', 'manager'}


class SensitiveMutationPermission(BasePermission):
    """Protège les modifications sensibles (PATCH/PUT/DELETE) aux rôles non gestionnaires."""

    message = 'Cette opération sensible exige un rôle de gestion ou d’administration.'

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        if getattr(request.user, 'is_superuser', False):
            return True
        return getattr(request.user, 'role', None) in {'admin', 'manager'}


def role_permission(module_name):
    """Factory de permission par rôle métier."""

    class RolePermission(BasePermission):
        message = 'Accès non autorisé pour votre rôle.'

        def has_permission(self, request, view):
            if not request.user or not request.user.is_authenticated:
                return False

            if getattr(request.user, 'is_superuser', False):
                return True

            role = getattr(request.user, 'role', None)
            if role == 'admin':
                return True

            allowed_modules = set(settings.ROLE_PERMISSIONS.get(role, set()))
            return 'all' in allowed_modules or module_name in allowed_modules

    return RolePermission
