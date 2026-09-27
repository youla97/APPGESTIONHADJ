from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.comptes.mixins import permission_metier
from apps.comptes.roles import Perm
from apps.journal.middleware import adresse_ip
from apps.journal.models import Historique
from apps.journal.services import journaliser
from apps.parametres.models import ParametreSysteme
from apps.pelerins.models import DossierHadj
from apps.pelerins.statuts import StatutDossier

from .models import Badge, VerificationBadge
from .qr import qr_png, url_verification


def _badge_accessible(request, pk):
    qs = request.user.filtrer_perimetre(Badge.objects.select_related("dossier__pelerin"), "dossier__pelerin__commune")
    return get_object_or_404(qs, pk=pk)


@require_POST
@permission_metier(Perm.BADGES_GENERER)
def generer(request, dossier_pk):
    dossiers = request.user.filtrer_perimetre(DossierHadj.objects.all(), "pelerin__commune")
    dossier = get_object_or_404(dossiers, pk=dossier_pk)
    if dossier.statut in (StatutDossier.BLOQUE, StatutDossier.REJETE, StatutDossier.ANNULE):
        messages.error(request, "Impossible de générer un badge pour un dossier bloqué, rejeté ou annulé.")
        return redirect("pelerins:detail", pk=dossier.pelerin_id)
    badge = Badge.objects.create(dossier=dossier)
    messages.success(request, "Badge généré.")
    return redirect("badges:imprimer", pk=badge.pk)


@permission_metier(Perm.BADGES_GENERER)
def imprimer(request, pk):
    badge = _badge_accessible(request, pk)
    if request.GET.get("confirmer"):
        badge.marquer_imprime()
        journaliser(Historique.Action.IMPRESSION, badge, requete=request)
        return HttpResponse(status=204)
    return render(request, "badges/badge.html", {
        "badge": badge,
        "dossier": badge.dossier,
        "pelerin": badge.dossier.pelerin,
        "parametres": ParametreSysteme.charger(),
    })


@permission_metier(Perm.BADGES_GENERER)
def qr_code(request, pk):
    badge = _badge_accessible(request, pk)
    return HttpResponse(qr_png(url_verification(request, badge)), content_type="image/png")


@permission_metier(Perm.BADGES_VERIFIER)
def scanner(request):
    """Page de contrôle : scan caméra ou saisie manuelle du jeton."""
    jeton = request.GET.get("jeton", "").strip()
    if jeton:
        # Accepte le jeton seul ou l'URL complète encodée dans le QR Code
        return redirect("badges:verifier", jeton=jeton.rstrip("/").rsplit("/", 1)[-1])
    return render(request, "badges/scanner.html")


@permission_metier(Perm.BADGES_VERIFIER)
def verifier(request, jeton):
    badge = Badge.objects.select_related("dossier__pelerin__commune", "dossier__passeport", "dossier__campagne") \
        .filter(jeton=jeton).first()
    derniere = badge.derniere_verification if badge else None

    if badge is None:
        resultat = VerificationBadge.Resultat.INCONNU
    elif not badge.est_actif:
        resultat = VerificationBadge.Resultat.REVOQUE
    elif badge.dossier.est_supprime or badge.dossier.statut in (
        StatutDossier.BLOQUE, StatutDossier.REJETE, StatutDossier.ANNULE
    ):
        resultat = VerificationBadge.Resultat.DOSSIER_INVALIDE
    else:
        resultat = VerificationBadge.Resultat.VALIDE

    VerificationBadge.objects.create(
        badge=badge, jeton_scanne=jeton[:128], resultat=resultat, controleur=request.user,
        lieu=request.GET.get("lieu", "")[:150], adresse_ip=adresse_ip(request),
    )
    if badge:
        Badge.objects.filter(pk=badge.pk).update(derniere_verification=timezone.now())
        journaliser(Historique.Action.CONTROLE_QR, badge, details=resultat, requete=request)

    return render(request, "badges/verification.html", {
        "badge": badge,
        "resultat": resultat,
        "Resultat": VerificationBadge.Resultat,
        "derniere_verification": derniere,
        "voir_details": request.user.a_permission(Perm.PELERINS_VOIR),
    })


@permission_metier(Perm.BADGES_GENERER)
def liste(request):
    badges = request.user.filtrer_perimetre(
        Badge.objects.select_related("dossier__pelerin", "dossier__campagne"), "dossier__pelerin__commune"
    ).filter(est_actif=True)
    etat = request.GET.get("etat")
    if etat == "imprimes":
        badges = badges.filter(nb_impressions__gt=0)
    elif etat == "non_imprimes":
        badges = badges.filter(nb_impressions=0)
    q = request.GET.get("q", "").strip()
    if q:
        badges = badges.filter(
            Q(dossier__numero__icontains=q) | Q(dossier__pelerin__nom__icontains=q)
            | Q(dossier__pelerin__prenom1__icontains=q)
        )
    return render(request, "badges/liste.html", {"badges": badges[:500], "etat": etat, "q": q})
