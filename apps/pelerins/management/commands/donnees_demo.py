"""
Crée une campagne, une agence, un groupe et quelques pèlerins fictifs pour
tester l'interface en développement. NE PAS UTILISER EN PRODUCTION.

    python manage.py donnees_demo [--nombre 40] [--admin]

--admin crée aussi le compte « demo » (administrateur national) avec le mot de
passe défini par la variable DEMO_PASSWORD du fichier .env.
"""
import random
from datetime import date, timedelta

import environ
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.comptes.models import Utilisateur
from apps.comptes.roles import Role
from apps.geographie.models import Commune
from apps.pelerins.models import Agence, CampagneHadj, DossierHadj, Groupe, Passeport, Pelerin

NOMS = ["DIALLO", "BAH", "BARRY", "SOW", "CAMARA", "CONDÉ", "KEITA", "TRAORÉ", "SYLLA", "TOURÉ", "KABA", "CISSÉ"]
PRENOMS_H = ["Mamadou", "Alpha", "Ibrahima", "Abdoulaye", "Ousmane", "Sékou", "Mohamed", "Thierno", "Amadou"]
PRENOMS_F = ["Fatoumata", "Aissatou", "Mariama", "Kadiatou", "Hawa", "Aminata", "Djénabou", "Oumou"]


class Command(BaseCommand):
    help = "Génère des données fictives de démonstration (développement uniquement)."

    def add_arguments(self, parser):
        parser.add_argument("--nombre", type=int, default=40)
        parser.add_argument("--admin", action="store_true", help="Crée le compte administrateur « demo ».")

    @transaction.atomic
    def handle(self, *args, nombre, admin, **options):
        if not settings.DEBUG:
            raise CommandError("Commande réservée au mode DEBUG.")
        communes = list(Commune.objects.all())
        if not communes:
            raise CommandError("Chargez d'abord le référentiel : python manage.py charger_geographie")

        if admin:
            mot_de_passe = environ.Env().str("DEMO_PASSWORD", default="")
            if not mot_de_passe:
                raise CommandError("Définissez DEMO_PASSWORD dans le fichier .env.")
            user, _ = Utilisateur.objects.get_or_create(
                username="demo", defaults={"role": Role.ADMIN_NATIONAL, "is_staff": True, "is_superuser": True,
                                           "first_name": "Compte", "last_name": "Démo"},
            )
            user.set_password(mot_de_passe)
            user.save()
            self.stdout.write("Compte « demo » prêt (mot de passe : DEMO_PASSWORD du .env).")

        aujourd_hui = date.today()
        campagne, _ = CampagneHadj.objects.get_or_create(annee=aujourd_hui.year + 1, defaults={
            "est_active": True,
            "date_depart_prevue": date(aujourd_hui.year + 1, 5, 10),
            "date_retour_prevue": date(aujourd_hui.year + 1, 6, 25),
        })
        agence, _ = Agence.objects.get_or_create(nom="Agence Démo Voyages", defaults={"sigle": "ADV"})
        groupe, _ = Groupe.objects.get_or_create(campagne=campagne, nom="Groupe A", defaults={"agence": agence})

        aleatoire = random.Random(42)
        debut = Pelerin.tous.count()
        for i in range(nombre):
            sexe = aleatoire.choice("MF")
            pelerin = Pelerin.objects.create(
                nom=aleatoire.choice(NOMS),
                prenom1=aleatoire.choice(PRENOMS_H if sexe == "M" else PRENOMS_F),
                sexe=sexe,
                date_naissance=date(aleatoire.randint(1945, 1990), aleatoire.randint(1, 12), aleatoire.randint(1, 28)),
                lieu_naissance=aleatoire.choice(["Conakry", "Labé", "Kankan", "Kindia", "Mamou", "Nzérékoré"]),
                telephone_principal=f"62{aleatoire.randint(1000000, 9999999)}",
                commune=aleatoire.choice(communes),
            )
            expiration = aujourd_hui + timedelta(days=aleatoire.choice([-60, 200, 400, 500, 1500, 2500]))
            passeport = Passeport.objects.create(
                pelerin=pelerin, numero=f"DEMO{debut + i:05d}",
                date_delivrance=expiration - timedelta(days=365 * 5), date_expiration=expiration,
            )
            dossier = DossierHadj.objects.create(
                pelerin=pelerin, campagne=campagne, passeport=passeport, agence=agence,
                groupe=groupe if aleatoire.random() < .5 else None,
            )
            dossier.calculer_completude()
        self.stdout.write(self.style.SUCCESS(f"{nombre} pèlerins fictifs créés pour {campagne}."))
