from functools import wraps

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class PermissionMetierMixin(LoginRequiredMixin):
    """Vue réservée aux utilisateurs ayant `permission_metier` (voir roles.Perm)."""

    permission_metier = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if self.permission_metier and not request.user.a_permission(self.permission_metier):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


def permission_metier(permission):
    """Équivalent décorateur de PermissionMetierMixin pour les vues fonctions."""

    def decorateur(vue):
        @wraps(vue)
        def enveloppe(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            if not request.user.a_permission(permission):
                raise PermissionDenied
            return vue(request, *args, **kwargs)

        return enveloppe

    return decorateur
