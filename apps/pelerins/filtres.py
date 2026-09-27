from django.db.models import Q

from .services import filtre_statut_passeport


def filtrer_pelerins(queryset, criteres: dict):
    """Applique les critères du RechercheForm (tous combinables)."""
    q = (criteres.get("q") or "").strip()
    if q:
        condition = Q()
        for mot in q.split():
            condition &= (
                Q(nom__icontains=mot) | Q(prenom1__icontains=mot) | Q(prenom2__icontains=mot)
                | Q(telephone_principal__icontains=mot) | Q(telephone_secondaire__icontains=mot)
                | Q(matricule__iexact=mot) | Q(passeports__numero__iexact=mot.upper())
                | Q(dossiers__numero__iexact=mot.upper())
            )
        queryset = queryset.filter(condition)

    if criteres.get("quartier"):
        queryset = queryset.filter(quartier=criteres["quartier"])
    elif criteres.get("commune"):
        queryset = queryset.filter(commune=criteres["commune"])
    elif criteres.get("prefecture"):
        queryset = queryset.filter(commune__prefecture=criteres["prefecture"])
    elif criteres.get("region"):
        queryset = queryset.filter(commune__prefecture__region=criteres["region"])

    if criteres.get("sexe"):
        queryset = queryset.filter(sexe=criteres["sexe"])

    dossier = Q()
    if criteres.get("campagne"):
        dossier &= Q(dossiers__campagne=criteres["campagne"])
    if criteres.get("groupe"):
        dossier &= Q(dossiers__groupe=criteres["groupe"])
    if criteres.get("statut_dossier"):
        dossier &= Q(dossiers__statut=criteres["statut_dossier"])
    if dossier:
        queryset = queryset.filter(dossier, dossiers__est_supprime=False)

    if criteres.get("statut_passeport"):
        queryset = queryset.filter(
            filtre_statut_passeport(criteres["statut_passeport"], "passeports__date_expiration"),
            passeports__est_actif=True, passeports__est_supprime=False,
        )
    return queryset.distinct()
