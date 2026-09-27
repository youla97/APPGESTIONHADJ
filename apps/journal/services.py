from django.contrib.contenttypes.models import ContentType

from .middleware import adresse_ip, utilisateur_courant
from .models import Historique


def journaliser(action, objet=None, details="", changements=None, utilisateur=None, requete=None):
    """Enregistre une opération dans l'historique. Utilisable depuis n'importe quelle vue."""
    if requete is not None and utilisateur is None and requete.user.is_authenticated:
        utilisateur = requete.user
    return Historique.objects.create(
        action=action,
        utilisateur=utilisateur or utilisateur_courant(),
        content_type=ContentType.objects.get_for_model(objet) if objet is not None else None,
        object_id=str(objet.pk) if objet is not None else "",
        objet_repr=str(objet)[:255] if objet is not None else "",
        changements=changements or {},
        details=details[:500],
        adresse_ip=adresse_ip(requete),
    )
