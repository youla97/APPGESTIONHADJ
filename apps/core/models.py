"""Modèles abstraits partagés par toutes les applications."""
from django.conf import settings
from django.db import models
from django.utils import timezone


class Horodatage(models.Model):
    """Date de création / modification et auteur."""

    cree_le = models.DateTimeField("créé le", auto_now_add=True, db_index=True)
    modifie_le = models.DateTimeField("modifié le", auto_now=True)
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="créé par", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+", editable=False,
    )
    modifie_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="modifié par", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+", editable=False,
    )

    class Meta:
        abstract = True


class ActifsManager(models.Manager):
    """Exclut les enregistrements supprimés logiquement."""

    def get_queryset(self):
        return super().get_queryset().filter(est_supprime=False)


class SuppressionLogique(models.Model):
    """Suppression logique (§20) : la donnée n'est jamais effacée physiquement."""

    est_supprime = models.BooleanField("supprimé", default=False, db_index=True, editable=False)
    supprime_le = models.DateTimeField("supprimé le", null=True, blank=True, editable=False)
    supprime_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="supprimé par", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+", editable=False,
    )
    motif_suppression = models.CharField("motif de suppression", max_length=255, blank=True, editable=False)

    objects = ActifsManager()
    tous = models.Manager()

    class Meta:
        abstract = True

    def supprimer(self, utilisateur=None, motif=""):
        self.est_supprime = True
        self.supprime_le = timezone.now()
        self.supprime_par = utilisateur
        self.motif_suppression = motif
        self.save(update_fields=["est_supprime", "supprime_le", "supprime_par", "motif_suppression"])

    def restaurer(self):
        self.est_supprime = False
        self.supprime_le = None
        self.supprime_par = None
        self.motif_suppression = ""
        self.save(update_fields=["est_supprime", "supprime_le", "supprime_par", "motif_suppression"])
