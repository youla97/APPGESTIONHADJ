"""
Règles métier : validité des passeports (§8, §9) et détection des doublons (§10).
"""
import calendar
from dataclasses import dataclass, field
from datetime import date

from django.db.models import Q
from django.utils import timezone

from apps.parametres.models import ParametreSysteme

from .statuts import StatutPasseport


def ajouter_mois(d: date, mois: int) -> date:
    m = d.month - 1 + mois
    annee, m = d.year + m // 12, m % 12 + 1
    return date(annee, m, min(d.day, calendar.monthrange(annee, m)[1]))


# --- Validité des passeports ----------------------------------------------------

@dataclass(frozen=True)
class SeuilsPasseport:
    aujourd_hui: date
    seuil_conformite: date  # expiration < seuil  → non conforme
    seuil_alerte: date      # expiration < seuil  → attention


def seuils_passeport(campagne=None, parametres=None, aujourd_hui=None) -> SeuilsPasseport:
    from .models import CampagneHadj

    parametres = parametres or ParametreSysteme.charger()
    aujourd_hui = aujourd_hui or timezone.localdate()
    campagne = campagne or CampagneHadj.active()

    reference = aujourd_hui
    if campagne:
        choix = ParametreSysteme.DateReference
        if parametres.date_reference == choix.RETOUR and campagne.date_retour_prevue:
            reference = campagne.date_retour_prevue
        elif parametres.date_reference == choix.DEPART and campagne.date_depart_prevue:
            reference = campagne.date_depart_prevue
    reference = max(reference, aujourd_hui)

    conformite = ajouter_mois(reference, parametres.validite_min_mois)
    return SeuilsPasseport(
        aujourd_hui=aujourd_hui,
        seuil_conformite=conformite,
        seuil_alerte=ajouter_mois(conformite, parametres.marge_alerte_mois),
    )


def evaluer_passeport(date_expiration: date, seuils: SeuilsPasseport | None = None) -> StatutPasseport:
    s = seuils or seuils_passeport()
    if date_expiration < s.aujourd_hui:
        return StatutPasseport.EXPIRE
    if date_expiration < s.seuil_conformite:
        return StatutPasseport.NON_CONFORME
    if date_expiration < s.seuil_alerte:
        return StatutPasseport.ATTENTION
    return StatutPasseport.CONFORME


def filtre_statut_passeport(statut, champ="date_expiration", seuils=None) -> Q:
    """Q() équivalent à `evaluer_passeport` pour filtrer en base (listes, exports, stats)."""
    s = seuils or seuils_passeport()
    return {
        StatutPasseport.EXPIRE: Q(**{f"{champ}__lt": s.aujourd_hui}),
        StatutPasseport.NON_CONFORME: Q(**{f"{champ}__gte": s.aujourd_hui, f"{champ}__lt": s.seuil_conformite}),
        StatutPasseport.ATTENTION: Q(**{f"{champ}__gte": s.seuil_conformite, f"{champ}__lt": s.seuil_alerte}),
        StatutPasseport.CONFORME: Q(**{f"{champ}__gte": s.seuil_alerte}),
    }[statut]


# --- Contrôle à la saisie du numéro de passeport (§8) ------------------------------

@dataclass
class ResultatControlePasseport:
    numero: str
    doublon: bool = False
    pelerin_existant: object = None
    statut: StatutPasseport | None = None
    bloquant: bool = False
    alertes: list = field(default_factory=list)

    def en_dict(self):
        p = self.pelerin_existant
        return {
            "numero": self.numero,
            "doublon": self.doublon,
            "pelerin_existant": {"id": p.pk, "matricule": p.matricule, "nom": p.nom_complet} if p else None,
            "statut": self.statut.value if self.statut else None,
            "statut_libelle": self.statut.label if self.statut else None,
            "bloquant": self.bloquant,
            "alertes": self.alertes,
        }


def controler_passeport(numero, date_expiration=None, exclure_pelerin_id=None) -> ResultatControlePasseport:
    from .models import Passeport, normaliser_numero_passeport

    numero = normaliser_numero_passeport(numero)
    res = ResultatControlePasseport(numero=numero)
    if not numero:
        return res

    existant = Passeport.objects.filter(numero=numero).select_related("pelerin")
    if exclure_pelerin_id:
        existant = existant.exclude(pelerin_id=exclure_pelerin_id)
    existant = existant.first()
    if existant:
        res.doublon = True
        res.bloquant = True
        res.pelerin_existant = existant.pelerin
        res.alertes.append({
            "niveau": "danger", "titre": "DOUBLON DÉTECTÉ",
            "message": f"Ce passeport est déjà enregistré pour {existant.pelerin.nom_complet} "
                       f"({existant.pelerin.matricule}).",
        })

    if date_expiration:
        parametres = ParametreSysteme.charger()
        res.statut = evaluer_passeport(date_expiration, seuils_passeport(parametres=parametres))
        if res.statut == StatutPasseport.EXPIRE:
            res.bloquant |= parametres.bloquer_passeport_expire
            res.alertes.append({"niveau": "danger", "titre": "PASSEPORT EXPIRÉ",
                                "message": "La date d'expiration est dépassée."})
        elif res.statut == StatutPasseport.NON_CONFORME:
            res.bloquant |= parametres.bloquer_passeport_non_conforme
            res.alertes.append({"niveau": "danger", "titre": "NON CONFORME",
                                "message": f"Validité inférieure aux {parametres.validite_min_mois} mois exigés."})
        elif res.statut == StatutPasseport.ATTENTION:
            res.alertes.append({"niveau": "warning", "titre": "ATTENTION",
                                "message": "Le passeport arrive prochainement à expiration."})
    return res


# --- Doublons potentiels (§10) -------------------------------------------------------

def rechercher_doublons_potentiels(nom, prenom1, date_naissance=None, telephone=None, exclure_pelerin_id=None):
    """
    Retourne une liste de (pelerin, critere, score) pour les correspondances probables
    sur l'identité ou le téléphone. Le contrôle sur le passeport est fait par `controler_passeport`.
    """
    from .models import Pelerin, SignalementDoublon

    critere = SignalementDoublon.Critere
    conditions = Q()
    if nom and prenom1 and date_naissance:
        conditions |= Q(nom__iexact=nom.strip(), prenom1__iexact=prenom1.strip(), date_naissance=date_naissance)
    if telephone:
        conditions |= Q(telephone_principal=telephone) | Q(telephone_secondaire=telephone)
    if not conditions:
        return []

    candidats = Pelerin.objects.filter(conditions)
    if exclure_pelerin_id:
        candidats = candidats.exclude(pk=exclure_pelerin_id)

    resultats = []
    for p in candidats[:20]:
        identite = (
            bool(nom and prenom1 and date_naissance)
            and p.nom.lower() == nom.strip().lower()
            and p.prenom1.lower() == prenom1.strip().lower()
            and p.date_naissance == date_naissance
        )
        tel = bool(telephone) and telephone in (p.telephone_principal, p.telephone_secondaire)
        if identite and tel:
            resultats.append((p, critere.COMBINAISON, 95))
        elif identite:
            resultats.append((p, critere.IDENTITE, 80))
        else:
            resultats.append((p, critere.TELEPHONE, 40))
    return sorted(resultats, key=lambda r: -r[2])
