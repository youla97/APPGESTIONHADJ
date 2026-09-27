from django.db import models


class StatutPasseport(models.TextChoices):
    """Classement des passeports (§9)."""

    CONFORME = "CONFORME", "Conforme"
    ATTENTION = "ATTENTION", "Attention"
    NON_CONFORME = "NON_CONFORME", "Non conforme"
    EXPIRE = "EXPIRE", "Expiré"


class StatutDossier(models.TextChoices):
    INCOMPLET = "INCOMPLET", "Incomplet"
    COMPLET = "COMPLET", "Complet"
    VALIDE = "VALIDE", "Validé"
    BLOQUE = "BLOQUE", "Bloqué"
    REJETE = "REJETE", "Rejeté"
    ANNULE = "ANNULE", "Annulé"


class StatutPelerin(models.TextChoices):
    INSCRIT = "INSCRIT", "Inscrit"
    CONFIRME = "CONFIRME", "Confirmé"
    PARTI = "PARTI", "Parti"
    RENTRE = "RENTRE", "Rentré"
    DESISTE = "DESISTE", "Désisté"
    DECEDE = "DECEDE", "Décédé"


COULEURS_STATUT_PASSEPORT = {
    StatutPasseport.CONFORME: "success",
    StatutPasseport.ATTENTION: "warning",
    StatutPasseport.NON_CONFORME: "danger",
    StatutPasseport.EXPIRE: "dark",
}
