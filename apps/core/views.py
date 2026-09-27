"""Tableau de bord (§6)."""
from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.views.generic import TemplateView

from apps.badges.models import Badge
from apps.pelerins.models import CampagneHadj, DossierHadj, Passeport, Pelerin, SignalementDoublon
from apps.pelerins.services import ajouter_mois, filtre_statut_passeport, seuils_passeport
from apps.pelerins.statuts import StatutDossier, StatutPasseport

TRANCHES_AGE = [(0, 39, "< 40 ans"), (40, 49, "40–49"), (50, 59, "50–59"), (60, 69, "60–69"), (70, 200, "70 ans et +")]


class TableauDeBordView(LoginRequiredMixin, TemplateView):
    template_name = "core/tableau_de_bord.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        auj = timezone.localdate()
        campagne = CampagneHadj.active()

        pelerins = user.filtrer_perimetre(Pelerin.objects.all())
        dossiers = user.filtrer_perimetre(DossierHadj.objects.all(), "pelerin__commune")
        if campagne:
            dossiers = dossiers.filter(campagne=campagne)
        passeports = user.filtrer_perimetre(Passeport.objects.filter(est_actif=True), "pelerin__commune")
        badges = user.filtrer_perimetre(Badge.objects.filter(est_actif=True), "dossier__pelerin__commune")
        seuils = seuils_passeport(campagne)

        par_statut = dict(dossiers.values_list("statut").annotate(n=Count("id")))
        statuts_passeport = {
            s: passeports.filter(filtre_statut_passeport(s, seuils=seuils)).count() for s in StatutPasseport
        }
        nb_dossiers = sum(par_statut.values())
        nb_badges_imprimes = badges.filter(nb_impressions__gt=0).count()

        ctx["campagne"] = campagne
        ctx["indicateurs"] = {
            "total": pelerins.count(),
            "jour": pelerins.filter(cree_le__date=auj).count(),
            "semaine": pelerins.filter(cree_le__date__gte=auj - timedelta(days=auj.weekday())).count(),
            "complets": par_statut.get(StatutDossier.COMPLET, 0) + par_statut.get(StatutDossier.VALIDE, 0),
            "incomplets": par_statut.get(StatutDossier.INCOMPLET, 0),
            "expires": statuts_passeport[StatutPasseport.EXPIRE],
            "proches_expiration": statuts_passeport[StatutPasseport.ATTENTION]
                                  + statuts_passeport[StatutPasseport.NON_CONFORME],
            "doublons": user.filtrer_perimetre(
                SignalementDoublon.objects.filter(decision=SignalementDoublon.Decision.A_TRAITER), "pelerin__commune"
            ).count(),
            "badges_imprimes": nb_badges_imprimes,
            "badges_non_imprimes": max(nb_dossiers - nb_badges_imprimes, 0),
        }

        # Graphiques
        depuis = auj - timedelta(days=29)
        evolution = dict(
            pelerins.filter(cree_le__date__gte=depuis).annotate(j=TruncDate("cree_le"))
            .values_list("j").annotate(n=Count("id"))
        )
        jours = [depuis + timedelta(days=i) for i in range(30)]
        par_region = pelerins.values_list("commune__prefecture__region__nom").annotate(n=Count("id")).order_by("-n")
        par_sexe = dict(pelerins.values_list("sexe").annotate(n=Count("id")))
        tranches = []
        for mini, maxi, libelle in TRANCHES_AGE:
            nes_apres = ajouter_mois(auj, -12 * (maxi + 1))
            nes_avant = ajouter_mois(auj, -12 * mini)
            tranches.append((libelle, pelerins.filter(
                date_naissance__gt=nes_apres, date_naissance__lte=nes_avant).count()))

        ctx["graphiques"] = {
            "evolution": {"labels": [j.strftime("%d/%m") for j in jours], "data": [evolution.get(j, 0) for j in jours]},
            "regions": {"labels": [r or "—" for r, _ in par_region], "data": [n for _, n in par_region]},
            "sexe": {"labels": ["Hommes", "Femmes"], "data": [par_sexe.get("M", 0), par_sexe.get("F", 0)]},
            "ages": {"labels": [t[0] for t in tranches], "data": [t[1] for t in tranches]},
            "dossiers": {
                "labels": [StatutDossier(s).label for s in par_statut],
                "data": list(par_statut.values()),
            },
            "passeports": {
                "labels": [s.label for s in statuts_passeport],
                "data": list(statuts_passeport.values()),
            },
        }
        return ctx
