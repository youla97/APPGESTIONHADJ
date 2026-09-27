"""
Badges et QR Codes (§14, §15).

Le QR Code n'encode qu'un jeton aléatoire non devinable (pas de données
personnelles) ; la vérification se fait côté serveur par un utilisateur authentifié.
"""
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import Horodatage


def generer_jeton():
    return secrets.token_urlsafe(24)


class Badge(Horodatage):
    dossier = models.ForeignKey(
        "pelerins.DossierHadj", verbose_name="dossier Hadj", on_delete=models.PROTECT, related_name="badges"
    )
    jeton = models.CharField("identifiant QR sécurisé", max_length=64, unique=True, default=generer_jeton, editable=False)
    est_actif = models.BooleanField("actif", default=True)
    motif_revocation = models.CharField("motif de révocation", max_length=255, blank=True)
    nb_impressions = models.PositiveIntegerField("nombre d'impressions", default=0, editable=False)
    derniere_impression = models.DateTimeField("dernière impression", null=True, blank=True, editable=False)
    derniere_verification = models.DateTimeField("dernière vérification", null=True, blank=True, editable=False)

    class Meta:
        verbose_name = "badge"
        ordering = ["-cree_le"]

    def __str__(self):
        return f"Badge {self.dossier.numero}"

    def save(self, *args, **kwargs):
        # Un seul badge actif par dossier : la réédition révoque l'ancien
        super().save(*args, **kwargs)
        if self.est_actif:
            Badge.objects.filter(dossier_id=self.dossier_id, est_actif=True).exclude(pk=self.pk).update(
                est_actif=False, motif_revocation="Remplacé par un nouveau badge"
            )

    @property
    def est_imprime(self):
        return self.nb_impressions > 0

    def marquer_imprime(self):
        self.nb_impressions += 1
        self.derniere_impression = timezone.now()
        Badge.objects.filter(pk=self.pk).update(
            nb_impressions=models.F("nb_impressions") + 1, derniere_impression=self.derniere_impression
        )


class VerificationBadge(models.Model):
    class Resultat(models.TextChoices):
        VALIDE = "VALIDE", "Badge valide"
        REVOQUE = "REVOQUE", "Badge révoqué"
        INCONNU = "INCONNU", "Badge inconnu"
        DOSSIER_INVALIDE = "DOSSIER_INVALIDE", "Dossier non valide"

    date = models.DateTimeField(auto_now_add=True, db_index=True)
    badge = models.ForeignKey(Badge, on_delete=models.SET_NULL, null=True, blank=True, related_name="verifications")
    jeton_scanne = models.CharField(max_length=128)
    resultat = models.CharField(max_length=20, choices=Resultat.choices)
    controleur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    lieu = models.CharField("lieu de contrôle", max_length=150, blank=True)
    adresse_ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = "vérification de badge"
        verbose_name_plural = "vérifications de badges"
        ordering = ["-date"]
