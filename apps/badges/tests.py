from datetime import date

from django.test import TestCase
from django.urls import reverse

from apps.comptes.models import Utilisateur
from apps.comptes.roles import Role
from apps.geographie.models import Commune, Prefecture, Region
from apps.pelerins.models import CampagneHadj, DossierHadj, Passeport, Pelerin
from apps.pelerins.statuts import StatutDossier

from .models import Badge, VerificationBadge


class BadgeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        commune = Commune.objects.create(
            nom="Kaloum", prefecture=Prefecture.objects.create(nom="Conakry", region=Region.objects.create(nom="Conakry"))
        )
        pelerin = Pelerin.objects.create(
            nom="Barry", prenom1="Alpha", sexe="M", date_naissance=date(1958, 2, 2),
            lieu_naissance="Mamou", telephone_principal="3", commune=commune,
        )
        passeport = Passeport.objects.create(pelerin=pelerin, numero="Q1", date_delivrance=date(2024, 1, 1),
                                             date_expiration=date(2034, 1, 1))
        cls.dossier = DossierHadj.objects.create(
            pelerin=pelerin, passeport=passeport, campagne=CampagneHadj.objects.create(annee=2027, est_active=True)
        )
        cls.admin = Utilisateur.objects.create_user("admin", password="x", role=Role.ADMIN_NATIONAL)
        cls.controleur = Utilisateur.objects.create_user("ctrl", password="x", role=Role.AGENT_CONTROLE)

    def test_generation_badge_et_qr(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse("badges:generer", args=[self.dossier.pk]))
        badge = Badge.objects.get()
        self.assertRedirects(r, reverse("badges:imprimer", args=[badge.pk]))
        self.assertContains(self.client.get(reverse("badges:imprimer", args=[badge.pk])), "HADJ 2027")
        qr = self.client.get(reverse("badges:qr", args=[badge.pk]))
        self.assertEqual(qr["Content-Type"], "image/png")
        # Le QR Code ne contient qu'un jeton aléatoire, pas de données personnelles
        self.assertNotIn("BARRY", badge.jeton)

    def test_reedition_revoque_ancien_badge(self):
        ancien = Badge.objects.create(dossier=self.dossier)
        nouveau = Badge.objects.create(dossier=self.dossier)
        ancien.refresh_from_db()
        self.assertFalse(ancien.est_actif)
        self.assertTrue(nouveau.est_actif)

    def test_verification_qr(self):
        badge = Badge.objects.create(dossier=self.dossier)
        self.client.force_login(self.controleur)
        r = self.client.get(reverse("badges:verifier", args=[badge.jeton]))
        self.assertContains(r, "BADGE VALIDE")
        self.assertContains(r, "BARRY")
        self.assertContains(self.client.get(reverse("badges:verifier", args=["inconnu"])), "BADGE INVALIDE")
        self.assertEqual(VerificationBadge.objects.count(), 2)

    def test_verification_dossier_bloque(self):
        badge = Badge.objects.create(dossier=self.dossier)
        DossierHadj.objects.filter(pk=self.dossier.pk).update(statut=StatutDossier.BLOQUE)
        self.client.force_login(self.controleur)
        self.assertContains(self.client.get(reverse("badges:verifier", args=[badge.jeton])), "BADGE INVALIDE")

    def test_controleur_ne_peut_pas_generer(self):
        self.client.force_login(self.controleur)
        self.assertEqual(self.client.post(reverse("badges:generer", args=[self.dossier.pk])).status_code, 403)
