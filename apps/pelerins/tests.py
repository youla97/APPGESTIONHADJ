"""Tests correspondant aux critères de validation du cahier des charges (§29)."""
from datetime import date

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.comptes.models import Utilisateur
from apps.comptes.roles import Role
from apps.geographie.models import Commune, Prefecture, Region
from apps.journal.models import Historique
from apps.parametres.models import ParametreSysteme

from .models import CampagneHadj, DossierHadj, Passeport, Pelerin, SignalementDoublon
from .services import ajouter_mois, evaluer_passeport, seuils_passeport
from .statuts import StatutDossier, StatutPasseport


class Donnees:
    @classmethod
    def creer_referentiel(cls):
        cls.region = Region.objects.create(nom="Conakry")
        cls.prefecture = Prefecture.objects.create(nom="Conakry", region=cls.region)
        cls.commune = Commune.objects.create(nom="Ratoma", prefecture=cls.prefecture)
        autre_pref = Prefecture.objects.create(nom="Kindia", region=Region.objects.create(nom="Kindia"))
        cls.autre_commune = Commune.objects.create(nom="Commune urbaine de Kindia", prefecture=autre_pref)
        cls.campagne = CampagneHadj.objects.create(annee=2027, est_active=True)
        cls.admin = Utilisateur.objects.create_user("admin", password="x", role=Role.ADMIN_NATIONAL)

    def donnees_formulaire(self, numero="AB123456", expiration=None, **extra):
        expiration = expiration or ajouter_mois(timezone.localdate(), 36)
        donnees = {
            "p-nom": "Diallo", "p-prenom1": "mamadou", "p-prenom2": "", "p-sexe": "M",
            "p-date_naissance": "1960-05-12", "p-lieu_naissance": "Labé", "p-nationalite": "Guinéenne",
            "p-telephone_principal": "620000001", "p-commune": self.commune.pk,
            "pp-numero": numero, "pp-date_delivrance": "2023-01-10",
            "pp-date_expiration": expiration.isoformat(), "pp-pays_delivrance": "Guinée",
            "d-campagne": self.campagne.pk, "d-statut_pelerin": "INSCRIT",
        }
        donnees.update(extra)
        return donnees


class EnregistrementTests(Donnees, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.creer_referentiel()

    def setUp(self):
        self.client.force_login(self.admin)

    def test_enregistrement_dossier(self):
        reponse = self.client.post(reverse("pelerins:creer"), self.donnees_formulaire())
        pelerin = Pelerin.objects.get()
        self.assertRedirects(reponse, reverse("pelerins:detail", args=[pelerin.pk]))
        self.assertEqual(pelerin.nom, "DIALLO")
        self.assertEqual(pelerin.matricule, f"PEL-{pelerin.pk:07d}")
        dossier = DossierHadj.objects.get()
        self.assertTrue(dossier.numero.startswith("H2027-"))
        self.assertEqual(dossier.passeport.numero, "AB123456")
        self.assertEqual(dossier.statut, StatutDossier.INCOMPLET)
        self.assertGreater(dossier.taux_completude, 0)
        self.assertEqual(pelerin.cree_par, self.admin)
        self.assertTrue(Historique.objects.filter(action=Historique.Action.CREATION, object_id=pelerin.pk).exists())

    def test_doublon_passeport_refuse(self):
        self.client.post(reverse("pelerins:creer"), self.donnees_formulaire(numero="AB123456"))
        reponse = self.client.post(
            reverse("pelerins:creer"),
            self.donnees_formulaire(numero="ab 123 456", **{"p-nom": "Camara", "p-telephone_principal": "621"}),
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "DOUBLON DÉTECTÉ")
        self.assertEqual(Pelerin.objects.count(), 1)

    def test_controle_passeport_ajax(self):
        self.client.post(reverse("pelerins:creer"), self.donnees_formulaire(numero="AB123456"))
        r = self.client.get(reverse("pelerins:controle_passeport"), {"numero": "ab123456"}).json()
        self.assertTrue(r["doublon"])
        r = self.client.get(reverse("pelerins:controle_passeport"),
                            {"numero": "ZZ999", "expiration": "2000-01-01"}).json()
        self.assertFalse(r["doublon"])
        self.assertEqual(r["statut"], StatutPasseport.EXPIRE)
        self.assertEqual(r["alertes"][0]["titre"], "PASSEPORT EXPIRÉ")

    def test_passeport_expire_bloque_dossier(self):
        self.client.post(reverse("pelerins:creer"), self.donnees_formulaire(expiration=date(2020, 1, 1), **{"pp-date_delivrance": "2015-01-01"}))
        self.assertEqual(DossierHadj.objects.get().statut, StatutDossier.BLOQUE)

    def test_passeport_expire_non_bloquant_selon_parametre(self):
        p = ParametreSysteme.charger()
        p.bloquer_passeport_expire = False
        p.save()
        self.client.post(reverse("pelerins:creer"), self.donnees_formulaire(expiration=date(2020, 1, 1), **{"pp-date_delivrance": "2015-01-01"}))
        self.assertEqual(DossierHadj.objects.get().statut, StatutDossier.INCOMPLET)

    def test_doublon_potentiel_identite(self):
        self.client.post(reverse("pelerins:creer"), self.donnees_formulaire(numero="AA1"))
        self.client.post(reverse("pelerins:creer"), self.donnees_formulaire(numero="BB2"))
        self.assertEqual(Pelerin.objects.count(), 2)
        signalement = SignalementDoublon.objects.get()
        self.assertEqual(signalement.critere, SignalementDoublon.Critere.COMBINAISON)

    def test_recherche_et_export(self):
        self.client.post(reverse("pelerins:creer"), self.donnees_formulaire())
        self.assertContains(self.client.get(reverse("pelerins:liste"), {"q": "diallo"}), "DIALLO")
        self.assertContains(self.client.get(reverse("pelerins:liste"), {"q": "AB123456"}), "DIALLO")
        self.assertNotContains(
            self.client.get(reverse("pelerins:liste"), {"commune": self.autre_commune.pk}), "DIALLO"
        )
        for fmt, type_mime in [("xlsx", "spreadsheetml"), ("csv", "text/csv"), ("pdf", "application/pdf")]:
            r = self.client.get(reverse("pelerins:liste"), {"region": self.region.pk, "export": fmt})
            self.assertIn(type_mime, r["Content-Type"])
        self.assertEqual(Historique.objects.filter(action=Historique.Action.EXPORT).count(), 3)

    def test_historique_modification(self):
        self.client.post(reverse("pelerins:creer"), self.donnees_formulaire())
        pelerin = Pelerin.objects.get()
        donnees = {k: v for k, v in self.donnees_formulaire().items() if k.startswith("p-")}
        donnees["p-telephone_principal"] = "629999999"
        self.client.post(reverse("pelerins:modifier", args=[pelerin.pk]), donnees)
        h = Historique.objects.get(action=Historique.Action.MODIFICATION, object_id=pelerin.pk)
        self.assertEqual(h.changements["telephone_principal"]["ancien"], "620000001")
        self.assertEqual(h.changements["telephone_principal"]["nouveau"], "629999999")
        self.assertEqual(h.utilisateur, self.admin)


class ActionsListeTests(Donnees, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.creer_referentiel()
        cls.consultation = Utilisateur.objects.create_user("lecteur", password="x", role=Role.CONSULTATION)

    def test_boutons_et_suppression_depuis_liste(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("pelerins:creer"), self.donnees_formulaire())
        pelerin = Pelerin.objects.get()
        liste = self.client.get(reverse("pelerins:liste"), {"q": "diallo"})
        self.assertContains(liste, reverse("pelerins:modifier", args=[pelerin.pk]))
        self.assertContains(liste, reverse("pelerins:supprimer", args=[pelerin.pk]))

        retour = reverse("pelerins:liste") + "?q=diallo"
        r = self.client.post(reverse("pelerins:supprimer", args=[pelerin.pk]), {"motif": "Test", "suivant": retour})
        self.assertRedirects(r, retour)
        self.assertFalse(Pelerin.objects.exists())

    def test_redirection_externe_refusee(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("pelerins:creer"), self.donnees_formulaire())
        pelerin = Pelerin.objects.get()
        r = self.client.post(reverse("pelerins:supprimer", args=[pelerin.pk]),
                             {"motif": "Test", "suivant": "https://exemple.com/"})
        self.assertRedirects(r, reverse("pelerins:liste"))

    def test_boutons_masques_sans_droit(self):
        Pelerin.objects.create(nom="Bah", prenom1="Awa", sexe="F", date_naissance=date(1970, 1, 1),
                               lieu_naissance="Pita", telephone_principal="5", commune=self.commune)
        self.client.force_login(self.consultation)
        liste = self.client.get(reverse("pelerins:liste"))
        self.assertContains(liste, "BAH")
        self.assertNotContains(liste, "bi-pencil")
        self.assertNotContains(liste, "bi-trash")


class PerimetreTests(Donnees, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.creer_referentiel()
        cls.agent = Utilisateur.objects.create_user(
            "agent", password="x", role=Role.AGENT_COMMUNAL, commune=cls.autre_commune
        )

    def test_agent_communal_ne_voit_que_sa_commune(self):
        pelerin = Pelerin.objects.create(
            nom="Bah", prenom1="Aissatou", sexe="F", date_naissance=date(1970, 1, 1),
            lieu_naissance="Conakry", telephone_principal="1", commune=self.commune,
        )
        self.client.force_login(self.agent)
        self.assertEqual(self.client.get(reverse("pelerins:detail", args=[pelerin.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("pelerins:liste")), "BAH")

    def test_agent_communal_ne_peut_pas_exporter_ni_journal(self):
        self.client.force_login(self.agent)
        self.assertEqual(self.client.get(reverse("journal:historique")).status_code, 403)


class ValiditePasseportTests(TestCase):
    def test_classement(self):
        auj = date(2026, 1, 15)
        campagne = CampagneHadj.objects.create(annee=2026, est_active=True, date_retour_prevue=date(2026, 6, 30))
        params = ParametreSysteme.charger()  # 6 mois après le retour + 3 mois d'alerte
        s = seuils_passeport(campagne, params, aujourd_hui=auj)
        self.assertEqual(s.seuil_conformite, date(2026, 12, 30))
        self.assertEqual(evaluer_passeport(date(2026, 1, 1), s), StatutPasseport.EXPIRE)
        self.assertEqual(evaluer_passeport(date(2026, 10, 1), s), StatutPasseport.NON_CONFORME)
        self.assertEqual(evaluer_passeport(date(2027, 2, 1), s), StatutPasseport.ATTENTION)
        self.assertEqual(evaluer_passeport(date(2028, 1, 1), s), StatutPasseport.CONFORME)

    def test_ajouter_mois(self):
        self.assertEqual(ajouter_mois(date(2024, 1, 31), 1), date(2024, 2, 29))
        self.assertEqual(ajouter_mois(date(2024, 3, 15), -3), date(2023, 12, 15))


class SuppressionLogiqueTests(Donnees, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.creer_referentiel()

    def test_suppression_logique_libere_le_numero(self):
        p = Pelerin.objects.create(
            nom="Sow", prenom1="Ibrahima", sexe="M", date_naissance=date(1965, 3, 3),
            lieu_naissance="Pita", telephone_principal="2", commune=self.commune,
        )
        Passeport.objects.create(pelerin=p, numero="X1", date_delivrance=date(2022, 1, 1),
                                 date_expiration=date(2032, 1, 1))
        p.supprimer(self.admin, "Erreur de saisie")
        self.assertFalse(Pelerin.objects.filter(pk=p.pk).exists())
        self.assertTrue(Pelerin.tous.filter(pk=p.pk, est_supprime=True).exists())
        self.assertTrue(Historique.objects.filter(action=Historique.Action.SUPPRESSION, object_id=p.pk).exists())
