"""
Journalisation automatique :
- création / modification / suppression logique des modèles suivis, avec
  ancienne et nouvelle valeur de chaque champ modifié (§19) ;
- renseignement automatique de cree_par / modifie_par ;
- connexions, déconnexions et échecs de connexion.
"""
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .middleware import adresse_ip, utilisateur_courant
from .models import Historique, JournalConnexion
from .services import journaliser

CHAMPS_IGNORES = {
    "modifie_le", "cree_le", "modifie_par", "cree_par", "supprime_le", "supprime_par", "last_login",
}
CHAMPS_MASQUES = {"password"}  # on trace le changement, jamais la valeur
MODELES_SUIVIS = []


def suivre(modele):
    """Active la journalisation automatique d'un modèle (appelé dans AppConfig.ready)."""
    MODELES_SUIVIS.append(modele)
    pre_save.connect(_avant_enregistrement, sender=modele, dispatch_uid=f"journal_pre_{modele._meta.label}")
    post_save.connect(_apres_enregistrement, sender=modele, dispatch_uid=f"journal_post_{modele._meta.label}")
    return modele


def _valeur(instance, champ):
    valeur = getattr(instance, champ.attname)
    if champ.is_relation and valeur is not None:
        cible = getattr(instance, champ.name, None)
        return str(cible) if cible is not None else valeur
    if hasattr(valeur, "name"):  # FieldFile
        return valeur.name or ""
    return valeur if isinstance(valeur, (str, int, float, bool, type(None))) else str(valeur)


def _etat(instance):
    return {
        f.name: _valeur(instance, f)
        for f in instance._meta.concrete_fields
        if f.name not in CHAMPS_IGNORES and not f.primary_key
    }


def _avant_enregistrement(sender, instance, **kwargs):
    utilisateur = utilisateur_courant()
    if utilisateur and hasattr(instance, "modifie_par_id"):
        instance.modifie_par = utilisateur
        if instance._state.adding:
            instance.cree_par = utilisateur

    instance._etat_precedent = None
    if not instance._state.adding and instance.pk:
        gestionnaire = getattr(sender, "tous", sender._default_manager)
        ancien = gestionnaire.filter(pk=instance.pk).first()
        if ancien is not None:
            instance._etat_precedent = _etat(ancien)


def _apres_enregistrement(sender, instance, created, **kwargs):
    if kwargs.get("raw"):
        return
    precedent = getattr(instance, "_etat_precedent", None)
    if created or precedent is None:
        journaliser(Historique.Action.CREATION, instance)
        return

    actuel = _etat(instance)
    changements = {
        champ: {
            "libelle": str(sender._meta.get_field(champ).verbose_name),
            "ancien": "••••" if champ in CHAMPS_MASQUES else precedent.get(champ),
            "nouveau": "••••" if champ in CHAMPS_MASQUES else valeur,
        }
        for champ, valeur in actuel.items()
        if precedent.get(champ) != valeur
    }
    if not changements:
        return
    action = Historique.Action.MODIFICATION
    if "est_supprime" in changements:
        action = Historique.Action.SUPPRESSION if actuel["est_supprime"] else Historique.Action.RESTAURATION
    journaliser(action, instance, changements=changements, details=getattr(instance, "motif_suppression", ""))


@receiver(user_logged_in)
def _connexion(sender, request, user, **kwargs):
    JournalConnexion.objects.create(
        utilisateur=user, identifiant_saisi=user.get_username(), evenement=JournalConnexion.Evenement.CONNEXION,
        adresse_ip=adresse_ip(request), navigateur=request.META.get("HTTP_USER_AGENT", "")[:255],
    )


@receiver(user_logged_out)
def _deconnexion(sender, request, user, **kwargs):
    if user is None:
        return
    JournalConnexion.objects.create(
        utilisateur=user, identifiant_saisi=user.get_username(), evenement=JournalConnexion.Evenement.DECONNEXION,
        adresse_ip=adresse_ip(request), navigateur=request.META.get("HTTP_USER_AGENT", "")[:255],
    )


@receiver(user_login_failed)
def _echec(sender, credentials, request=None, **kwargs):
    JournalConnexion.objects.create(
        identifiant_saisi=str(credentials.get("username", ""))[:150], evenement=JournalConnexion.Evenement.ECHEC,
        adresse_ip=adresse_ip(request),
        navigateur=request.META.get("HTTP_USER_AGENT", "")[:255] if request else "",
    )
