"""Rend la requête courante accessible aux signaux (utilisateur, adresse IP)."""
from contextvars import ContextVar

_requete_courante: ContextVar = ContextVar("requete_courante", default=None)


def requete_courante():
    return _requete_courante.get()


def utilisateur_courant():
    requete = requete_courante()
    user = getattr(requete, "user", None)
    return user if user is not None and user.is_authenticated else None


def adresse_ip(requete=None):
    requete = requete or requete_courante()
    if requete is None:
        return None
    transmis = requete.META.get("HTTP_X_FORWARDED_FOR")
    return transmis.split(",")[0].strip() if transmis else requete.META.get("REMOTE_ADDR")


class RequeteCouranteMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        jeton = _requete_courante.set(request)
        try:
            return self.get_response(request)
        finally:
            _requete_courante.reset(jeton)
