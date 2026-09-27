from django.core.validators import MinValueValidator
from django.db import models


class ParametreSysteme(models.Model):
    """Paramétrage global (enregistrement unique, pk=1)."""

    class DateReference(models.TextChoices):
        AUJOURDHUI = "AUJOURDHUI", "Date du jour"
        DEPART = "DEPART", "Date de départ prévue de la campagne"
        RETOUR = "RETOUR", "Date de retour prévue de la campagne"

    # §9 — Règle de validité des passeports
    validite_min_mois = models.PositiveSmallIntegerField(
        "validité minimale exigée (mois)", default=6, validators=[MinValueValidator(0)],
        help_text="Le passeport doit rester valide au moins ce nombre de mois après la date de référence.",
    )
    marge_alerte_mois = models.PositiveSmallIntegerField(
        "marge d'alerte (mois)", default=3,
        help_text="Au-delà du seuil minimal, période pendant laquelle le passeport est signalé « Attention ».",
    )
    date_reference = models.CharField(
        "date de référence du contrôle", max_length=15,
        choices=DateReference.choices, default=DateReference.RETOUR,
    )
    bloquer_passeport_expire = models.BooleanField("bloquer les dossiers avec passeport expiré", default=True)
    bloquer_passeport_non_conforme = models.BooleanField(
        "bloquer les dossiers avec passeport non conforme", default=False
    )

    # Badges / QR Code (§14)
    afficher_passeport_sur_badge = models.BooleanField(
        "afficher le n° de passeport sur le badge", default=False,
        help_text="Sinon, seul le numéro de dossier est imprimé.",
    )

    modifie_le = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "paramètres système"
        verbose_name_plural = "paramètres système"

    def __str__(self):
        return "Paramètres système"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def charger(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
