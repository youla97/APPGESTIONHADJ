from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Historique(models.Model):
    """Journal des opérations importantes (§19)."""

    class Action(models.TextChoices):
        CREATION = "CREATION", "Création"
        MODIFICATION = "MODIFICATION", "Modification"
        SUPPRESSION = "SUPPRESSION", "Suppression logique"
        RESTAURATION = "RESTAURATION", "Restauration"
        VALIDATION = "VALIDATION", "Validation"
        EXPORT = "EXPORT", "Export"
        IMPRESSION = "IMPRESSION", "Impression"
        CONTROLE_QR = "CONTROLE_QR", "Contrôle QR Code"
        FUSION = "FUSION", "Fusion de doublons"

    date = models.DateTimeField("date / heure", auto_now_add=True, db_index=True)
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="utilisateur", on_delete=models.SET_NULL, null=True, blank=True
    )
    action = models.CharField("action", max_length=20, choices=Action.choices, db_index=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.CharField(max_length=64, blank=True, db_index=True)
    objet = GenericForeignKey("content_type", "object_id")
    objet_repr = models.CharField("objet", max_length=255, blank=True)
    # {"champ": {"libelle": ..., "ancien": ..., "nouveau": ...}}
    changements = models.JSONField("changements", default=dict, blank=True)
    details = models.CharField("détails", max_length=500, blank=True)
    adresse_ip = models.GenericIPAddressField("adresse IP", null=True, blank=True)

    class Meta:
        verbose_name = "historique"
        verbose_name_plural = "historique"
        ordering = ["-date"]
        indexes = [models.Index(fields=["content_type", "object_id"])]

    def __str__(self):
        return f"{self.date:%d/%m/%Y %H:%M} – {self.get_action_display()} – {self.objet_repr}"


class JournalConnexion(models.Model):
    class Evenement(models.TextChoices):
        CONNEXION = "CONNEXION", "Connexion"
        DECONNEXION = "DECONNEXION", "Déconnexion"
        ECHEC = "ECHEC", "Échec de connexion"

    date = models.DateTimeField(auto_now_add=True, db_index=True)
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    identifiant_saisi = models.CharField("identifiant saisi", max_length=150, blank=True)
    evenement = models.CharField("événement", max_length=15, choices=Evenement.choices)
    adresse_ip = models.GenericIPAddressField("adresse IP", null=True, blank=True)
    navigateur = models.CharField("navigateur", max_length=255, blank=True)

    class Meta:
        verbose_name = "journal de connexion"
        verbose_name_plural = "journal des connexions"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.date:%d/%m/%Y %H:%M} – {self.get_evenement_display()} – {self.identifiant_saisi}"
