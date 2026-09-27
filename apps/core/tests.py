from datetime import date

from django.test import TestCase
from django.urls import reverse

from apps.badges.models import Badge
from apps.comptes.models import Utilisateur
from apps.comptes.roles import Role
from apps.geographie.models import Commune, Prefecture, Region
from apps.pelerins.models import CampagneHadj, DossierHadj, Passeport, Pelerin


class PagesTests(TestCase):
    """Toutes les pages principales s'affichent sans erreur."""

    @classmethod
    def setUpTestData(cls):
        commune = Commune.objects.create(
            nom="Dixinn", prefecture=Prefecture.objects.create(nom="Conakry", region=Region.objects.create(nom="Conakry"))
        )
        cls.pelerin = Pelerin.objects.create(
            nom="Keita", prenom1="Sékou", sexe="M", date_naissance=date(1962, 7, 7),
            lieu_naissance="Kankan", telephone_principal="4", commune=commune,
        )
        passeport = Passeport.objects.create(pelerin=cls.pelerin, numero="P1", date_delivrance=date(2024, 1, 1),
                                             date_expiration=date(2034, 1, 1))
        dossier = DossierHadj.objects.create(pelerin=cls.pelerin, passeport=passeport,
                                             campagne=CampagneHadj.objects.create(annee=2027, est_active=True))
        cls.badge = Badge.objects.create(dossier=dossier)
        cls.admin = Utilisateur.objects.create_user("admin", password="x", role=Role.ADMIN_NATIONAL, is_staff=True)

    def test_pages(self):
        self.client.force_login(self.admin)
        for url in [
            reverse("core:tableau_de_bord"), reverse("pelerins:liste"), reverse("pelerins:creer"),
            reverse("pelerins:detail", args=[self.pelerin.pk]), reverse("pelerins:modifier", args=[self.pelerin.pk]),
            reverse("pelerins:doublons"), reverse("badges:liste"), reverse("badges:scanner"),
            reverse("badges:imprimer", args=[self.badge.pk]), reverse("journal:historique"),
            reverse("journal:connexions"), reverse("password_change"),
            reverse("geographie:prefectures") + "?region=1",
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_connexion_requise(self):
        self.assertRedirects(self.client.get("/"), reverse("login") + "?next=/")
