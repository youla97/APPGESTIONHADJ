"""
Rôles et droits applicatifs (§5 du cahier des charges).

Chaque rôle reçoit un ensemble de permissions « métier ». Le périmètre
géographique (région / préfecture / commune) limite en plus les données
visibles : voir `Utilisateur.filtrer_perimetre`.
"""
from django.db import models


class Role(models.TextChoices):
    ADMIN_NATIONAL = "ADMIN_NATIONAL", "Administrateur national"
    ADMIN_REGIONAL = "ADMIN_REGIONAL", "Administrateur régional"
    ADMIN_PREFECTORAL = "ADMIN_PREFECTORAL", "Administrateur préfectoral"
    AGENT_COMMUNAL = "AGENT_COMMUNAL", "Agent communal"
    AGENT_CONTROLE = "AGENT_CONTROLE", "Agent de contrôle"
    CONSULTATION = "CONSULTATION", "Utilisateur consultation"


class Perm:
    PELERINS_VOIR = "pelerins.voir"
    PELERINS_CREER = "pelerins.creer"
    PELERINS_MODIFIER = "pelerins.modifier"
    PELERINS_SUPPRIMER = "pelerins.supprimer"
    DOSSIERS_VALIDER = "dossiers.valider"
    DOUBLONS_TRAITER = "doublons.traiter"
    PASSEPORTS_CONTROLER = "passeports.controler"
    BADGES_GENERER = "badges.generer"
    BADGES_VERIFIER = "badges.verifier"
    EXPORTS = "exports"
    STATISTIQUES = "statistiques"
    UTILISATEURS_GERER = "utilisateurs.gerer"
    PARAMETRES_GERER = "parametres.gerer"
    JOURNAL_VOIR = "journal.voir"


_ADMIN_ZONE = {
    Perm.PELERINS_VOIR, Perm.PELERINS_CREER, Perm.PELERINS_MODIFIER, Perm.PELERINS_SUPPRIMER,
    Perm.DOSSIERS_VALIDER, Perm.DOUBLONS_TRAITER, Perm.PASSEPORTS_CONTROLER,
    Perm.BADGES_GENERER, Perm.BADGES_VERIFIER, Perm.EXPORTS, Perm.STATISTIQUES, Perm.JOURNAL_VOIR,
}

PERMISSIONS_PAR_ROLE = {
    Role.ADMIN_NATIONAL: {v for k, v in vars(Perm).items() if not k.startswith("_")},
    Role.ADMIN_REGIONAL: _ADMIN_ZONE,
    Role.ADMIN_PREFECTORAL: _ADMIN_ZONE,
    Role.AGENT_COMMUNAL: {
        Perm.PELERINS_VOIR, Perm.PELERINS_CREER, Perm.PELERINS_MODIFIER, Perm.PASSEPORTS_CONTROLER,
    },
    Role.AGENT_CONTROLE: {
        Perm.PELERINS_VOIR, Perm.PASSEPORTS_CONTROLER, Perm.BADGES_VERIFIER,
    },
    Role.CONSULTATION: {Perm.PELERINS_VOIR, Perm.STATISTIQUES},
}
