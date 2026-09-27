from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_GET, require_POST

from apps.comptes.mixins import permission_metier
from apps.comptes.roles import Perm
from apps.journal.models import Historique
from apps.journal.services import journaliser

from . import exports
from .filtres import filtrer_pelerins
from .forms import DocumentForm, DossierHadjForm, PasseportForm, PelerinForm, RechercheForm
from .models import DossierHadj, Pelerin, SignalementDoublon
from .services import controler_passeport, rechercher_doublons_potentiels, seuils_passeport, evaluer_passeport
from .statuts import COULEURS_STATUT_PASSEPORT, StatutDossier, StatutPasseport


def pelerins_visibles(user):
    return user.filtrer_perimetre(Pelerin.objects.all())


def _signaler_doublons(pelerin):
    for autre, critere, score in rechercher_doublons_potentiels(
        pelerin.nom, pelerin.prenom1, pelerin.date_naissance, pelerin.telephone_principal,
        exclure_pelerin_id=pelerin.pk,
    ):
        SignalementDoublon.objects.get_or_create(
            pelerin=pelerin, pelerin_similaire=autre, defaults={"critere": critere, "score": score}
        )


# --- Liste / recherche -----------------------------------------------------------

@permission_metier(Perm.PELERINS_VOIR)
def liste(request):
    form = RechercheForm(request.GET or None)
    pelerins = pelerins_visibles(request.user)
    if form.is_valid():
        pelerins = filtrer_pelerins(pelerins, form.cleaned_data)

    format_export = request.GET.get("export")
    if format_export:
        if not request.user.a_permission(Perm.EXPORTS):
            messages.error(request, "Vous n'avez pas le droit d'exporter.")
        else:
            journaliser(Historique.Action.EXPORT, details=f"{format_export} – {request.GET.urlencode()}",
                        requete=request)
            fonction = {"csv": exports.export_csv, "xlsx": exports.export_excel, "pdf": exports.export_pdf}.get(
                format_export
            )
            if fonction:
                return fonction(pelerins)

    page = Paginator(
        pelerins.select_related("commune__prefecture__region", "quartier").order_by("nom", "prenom1"), 25
    ).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    params.pop("export", None)
    return render(request, "pelerins/liste.html", {
        "form": form, "page": page, "total": page.paginator.count, "params": params.urlencode(),
    })


# --- Enregistrement ----------------------------------------------------------------

@permission_metier(Perm.PELERINS_CREER)
def creer(request):
    donnees = request.POST if request.method == "POST" else None
    fichiers = request.FILES if request.method == "POST" else None
    f_pelerin = PelerinForm(donnees, fichiers, prefix="p", utilisateur=request.user)
    f_passeport = PasseportForm(donnees, fichiers, prefix="pp")
    f_dossier = DossierHadjForm(donnees, prefix="d")

    if request.method == "POST" and all(f.is_valid() for f in (f_pelerin, f_passeport, f_dossier)):
        with transaction.atomic():
            pelerin = f_pelerin.save()
            passeport = f_passeport.save(commit=False)
            passeport.pelerin = pelerin
            passeport.save()
            dossier = f_dossier.save(commit=False)
            dossier.pelerin = pelerin
            dossier.passeport = passeport
            if f_passeport.controle and f_passeport.controle.bloquant:
                dossier.statut = StatutDossier.BLOQUE
            dossier.save()
            dossier.calculer_completude()
            _signaler_doublons(pelerin)
        for alerte in (f_passeport.controle.alertes if f_passeport.controle else []):
            messages.warning(request, f"{alerte['titre']} : {alerte['message']}")
        messages.success(request, f"Pèlerin {pelerin.nom_complet} enregistré (dossier {dossier.numero}).")
        return redirect("pelerins:detail", pk=pelerin.pk)

    return render(request, "pelerins/formulaire.html", {
        "f_pelerin": f_pelerin, "f_passeport": f_passeport, "f_dossier": f_dossier, "titre": "Nouveau pèlerin",
    })


@permission_metier(Perm.PELERINS_MODIFIER)
def modifier(request, pk):
    pelerin = get_object_or_404(pelerins_visibles(request.user), pk=pk)
    f_pelerin = PelerinForm(request.POST or None, request.FILES or None, instance=pelerin, prefix="p",
                            utilisateur=request.user)
    if request.method == "POST" and f_pelerin.is_valid():
        f_pelerin.save()
        for dossier in pelerin.dossiers.all():
            dossier.calculer_completude()
        messages.success(request, "Fiche mise à jour.")
        return redirect("pelerins:detail", pk=pelerin.pk)
    return render(request, "pelerins/formulaire.html", {
        "f_pelerin": f_pelerin, "titre": f"Modifier – {pelerin.nom_complet}", "pelerin": pelerin,
    })


@require_POST
@permission_metier(Perm.PELERINS_SUPPRIMER)
def supprimer(request, pk):
    pelerin = get_object_or_404(pelerins_visibles(request.user), pk=pk)
    suivant = request.POST.get("suivant", "")
    if not url_has_allowed_host_and_scheme(suivant, {request.get_host()}, request.is_secure()):
        suivant = ""
    motif = request.POST.get("motif", "").strip()
    if not motif:
        messages.error(request, "Le motif de suppression est obligatoire.")
        return redirect(suivant or reverse("pelerins:detail", args=[pk]))
    pelerin.supprimer(request.user, motif)
    messages.success(request, f"{pelerin.nom_complet} supprimé (suppression logique, restaurable par l'administrateur).")
    return redirect(suivant or reverse("pelerins:liste"))


# --- Fiche individuelle (§12) --------------------------------------------------------

@permission_metier(Perm.PELERINS_VOIR)
def detail(request, pk):
    pelerin = get_object_or_404(
        pelerins_visibles(request.user).select_related("commune__prefecture__region", "quartier"), pk=pk
    )
    seuils = seuils_passeport()
    passeports = [(p, evaluer_passeport(p.date_expiration, seuils)) for p in pelerin.passeports.all()]
    dossiers = pelerin.dossiers.select_related("campagne", "agence", "groupe", "passeport").prefetch_related("badges")

    form_document = DocumentForm(prefix="doc")
    if request.method == "POST" and request.user.a_permission(Perm.PELERINS_MODIFIER):
        form_document = DocumentForm(request.POST, request.FILES, prefix="doc")
        if form_document.is_valid():
            document = form_document.save(commit=False)
            document.pelerin = pelerin
            document.dossier = dossiers.first()
            document.save()
            for dossier in dossiers:
                dossier.calculer_completude()
            messages.success(request, "Document ajouté.")
            return redirect("pelerins:detail", pk=pk)

    historique = Historique.objects.filter(
        content_type__app_label="pelerins", content_type__model="pelerin", object_id=str(pelerin.pk)
    ).select_related("utilisateur")[:20]

    return render(request, "pelerins/detail.html", {
        "pelerin": pelerin,
        "passeports": passeports,
        "couleurs": COULEURS_STATUT_PASSEPORT,
        "dossiers": dossiers,
        "documents": pelerin.documents.all(),
        "form_document": form_document,
        "doublons": pelerin.doublons_signales.filter(decision=SignalementDoublon.Decision.A_TRAITER)
            .select_related("pelerin_similaire"),
        "historique": historique,
    })


@require_POST
@permission_metier(Perm.DOSSIERS_VALIDER)
def valider_dossier(request, pk):
    dossier = get_object_or_404(
        request.user.filtrer_perimetre(DossierHadj.objects.all(), "pelerin__commune"), pk=pk
    )
    manquants = dossier.calculer_completude()
    if manquants:
        messages.error(request, "Dossier incomplet : " + ", ".join(manquants))
    elif dossier.passeport and evaluer_passeport(dossier.passeport.date_expiration) == StatutPasseport.EXPIRE:
        messages.error(request, "Passeport expiré : validation impossible.")
    else:
        dossier.statut = StatutDossier.VALIDE
        dossier.valide_par = request.user
        dossier.valide_le = timezone.now()
        dossier.save()
        journaliser(Historique.Action.VALIDATION, dossier, requete=request)
        messages.success(request, f"Dossier {dossier.numero} validé.")
    return redirect("pelerins:detail", pk=dossier.pelerin_id)


# --- Contrôle du passeport en temps réel (§8) ------------------------------------------

@require_GET
@permission_metier(Perm.PASSEPORTS_CONTROLER)
def controle_passeport(request):
    resultat = controler_passeport(
        request.GET.get("numero", ""),
        parse_date(request.GET.get("expiration", "") or "") or None,
        exclure_pelerin_id=request.GET.get("pelerin") or None,
    )
    return JsonResponse(resultat.en_dict())


# --- Doublons (§10) ----------------------------------------------------------------

@permission_metier(Perm.DOUBLONS_TRAITER)
def doublons(request):
    signalements = SignalementDoublon.objects.filter(decision=SignalementDoublon.Decision.A_TRAITER).select_related(
        "pelerin__commune", "pelerin_similaire__commune"
    )
    signalements = request.user.filtrer_perimetre(signalements, "pelerin__commune")
    return render(request, "pelerins/doublons.html", {"signalements": signalements[:200]})


@require_POST
@permission_metier(Perm.DOUBLONS_TRAITER)
def traiter_doublon(request, pk):
    signalement = get_object_or_404(
        request.user.filtrer_perimetre(SignalementDoublon.objects.all(), "pelerin__commune"), pk=pk
    )
    decision = request.POST.get("decision")
    if decision not in (SignalementDoublon.Decision.CONFIRME, SignalementDoublon.Decision.CONSERVE):
        messages.error(request, "Décision invalide.")
    elif decision == SignalementDoublon.Decision.CONSERVE and not request.POST.get("justification", "").strip():
        messages.error(request, "Une justification est requise pour conserver les deux dossiers.")
    else:
        signalement.decision = decision
        signalement.justification = request.POST.get("justification", "").strip()
        signalement.traite_par = request.user
        signalement.traite_le = timezone.now()
        signalement.save()
        messages.success(request, "Signalement traité.")
    return redirect("pelerins:doublons")
