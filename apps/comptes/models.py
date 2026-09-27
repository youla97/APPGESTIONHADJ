from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models

from .roles import PERMISSIONS_PAR_ROLE, Role


class Utilisateur(AbstractUser):
    role = models.CharField("rôle", max_length=30, choices=Role.choices, default=Role.CONSULTATION)
    telephone = models.CharField("téléphone", max_length=30, blank=True)
    fonction = models.CharField("fonction", max_length=120, blank=True)

    # Périmètre géographique selon le rôle
    region = models.ForeignKey(
        "geographie.Region", verbose_name="région", on_delete=models.PROTECT, null=True, blank=True
    )
    prefecture = models.ForeignKey(
        "geographie.Prefecture", verbose_name="préfecture", on_delete=models.PROTECT, null=True, blank=True
    )
    commune = models.ForeignKey(
        "geographie.Commune", verbose_name="commune", on_delete=models.PROTECT, null=True, blank=True
    )

    class Meta:
        verbose_name = "utilisateur"

    def __str__(self):
        return self.get_full_name() or self.username

    def clean(self):
        super().clean()
        requis = {
            Role.ADMIN_REGIONAL: ("region", "une région"),
            Role.ADMIN_PREFECTORAL: ("prefecture", "une préfecture"),
            Role.AGENT_COMMUNAL: ("commune", "une commune"),
        }.get(self.role)
        if requis and not getattr(self, f"{requis[0]}_id"):
            raise ValidationError({requis[0]: f"Ce rôle doit être rattaché à {requis[1]}."})

    def save(self, *args, **kwargs):
        # Compléter automatiquement les niveaux supérieurs du périmètre
        if self.commune_id and not self.prefecture_id:
            self.prefecture_id = self.commune.prefecture_id
        if self.prefecture_id and not self.region_id:
            self.region_id = self.prefecture.region_id
        super().save(*args, **kwargs)

    # --- Droits -----------------------------------------------------------
    @property
    def est_admin_national(self):
        return self.is_superuser or self.role == Role.ADMIN_NATIONAL

    def a_permission(self, permission):
        if not self.is_active:
            return False
        if self.is_superuser:
            return True
        return permission in PERMISSIONS_PAR_ROLE.get(self.role, set())

    def filtrer_perimetre(self, queryset, chemin_commune="commune"):
        """
        Restreint un queryset au périmètre géographique de l'utilisateur.
        `chemin_commune` est le chemin ORM vers la commune (ex. "pelerin__commune").
        """
        if self.est_admin_national:
            return queryset
        # Le niveau le plus fin renseigné détermine le périmètre
        if self.commune_id:
            return queryset.filter(**{f"{chemin_commune}_id": self.commune_id})
        if self.prefecture_id:
            return queryset.filter(**{f"{chemin_commune}__prefecture_id": self.prefecture_id})
        if self.region_id:
            return queryset.filter(**{f"{chemin_commune}__prefecture__region_id": self.region_id})
        # Sans rattachement : les rôles de contrôle/consultation ont une portée nationale
        if self.role in (Role.AGENT_CONTROLE, Role.CONSULTATION):
            return queryset
        return queryset.none()
