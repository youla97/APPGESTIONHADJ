"""Référentiel géographique : Région → Préfecture → Commune → Quartier (§4)."""
from django.db import models


class ZoneBase(models.Model):
    code = models.CharField("code", max_length=20, blank=True)
    nom = models.CharField("nom", max_length=120)
    actif = models.BooleanField("actif", default=True)

    class Meta:
        abstract = True
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Region(ZoneBase):
    class Meta(ZoneBase.Meta):
        verbose_name = "région"
        constraints = [models.UniqueConstraint(fields=["nom"], name="region_nom_unique")]


class Prefecture(ZoneBase):
    region = models.ForeignKey(Region, verbose_name="région", on_delete=models.PROTECT, related_name="prefectures")

    class Meta(ZoneBase.Meta):
        verbose_name = "préfecture"
        constraints = [models.UniqueConstraint(fields=["region", "nom"], name="prefecture_nom_unique")]


class Commune(ZoneBase):
    prefecture = models.ForeignKey(
        Prefecture, verbose_name="préfecture", on_delete=models.PROTECT, related_name="communes"
    )

    class Meta(ZoneBase.Meta):
        verbose_name = "commune"
        constraints = [models.UniqueConstraint(fields=["prefecture", "nom"], name="commune_nom_unique")]

    @property
    def region(self):
        return self.prefecture.region


class Quartier(ZoneBase):
    commune = models.ForeignKey(Commune, verbose_name="commune", on_delete=models.PROTECT, related_name="quartiers")

    class Meta(ZoneBase.Meta):
        verbose_name = "quartier / district"
        verbose_name_plural = "quartiers / districts"
        constraints = [models.UniqueConstraint(fields=["commune", "nom"], name="quartier_nom_unique")]
