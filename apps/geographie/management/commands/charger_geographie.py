"""
Charge le référentiel de base : 8 régions administratives et 33 préfectures
+ la zone spéciale de Conakry.

Pour chaque préfecture, seule la commune urbaine est créée ; les communes
rurales et les quartiers/districts doivent être complétés par l'administration
(interface d'administration ou import), conformément au §4 du cahier des charges.

    python manage.py charger_geographie
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.geographie.models import Commune, Prefecture, Region

REFERENTIEL = {
    "Boké": ["Boffa", "Boké", "Fria", "Gaoual", "Koundara"],
    "Conakry": ["Conakry"],
    "Faranah": ["Dabola", "Dinguiraye", "Faranah", "Kissidougou"],
    "Kankan": ["Kankan", "Kérouané", "Kouroussa", "Mandiana", "Siguiri"],
    "Kindia": ["Coyah", "Dubréka", "Forécariah", "Kindia", "Télimélé"],
    "Labé": ["Koubia", "Labé", "Lélouma", "Mali", "Tougué"],
    "Mamou": ["Dalaba", "Mamou", "Pita"],
    "Nzérékoré": ["Beyla", "Guéckédou", "Lola", "Macenta", "Nzérékoré", "Yomou"],
}

COMMUNES_CONAKRY = ["Kaloum", "Dixinn", "Matam", "Ratoma", "Matoto"]


class Command(BaseCommand):
    help = "Charge les régions, préfectures et communes urbaines de Guinée."

    @transaction.atomic
    def handle(self, *args, **options):
        nb = 0
        for nom_region, prefectures in REFERENTIEL.items():
            region, _ = Region.objects.get_or_create(nom=nom_region)
            for nom_pref in prefectures:
                pref, _ = Prefecture.objects.get_or_create(region=region, nom=nom_pref)
                communes = COMMUNES_CONAKRY if nom_region == "Conakry" else [f"Commune urbaine de {nom_pref}"]
                for nom_commune in communes:
                    _, cree = Commune.objects.get_or_create(prefecture=pref, nom=nom_commune)
                    nb += cree
        self.stdout.write(self.style.SUCCESS(
            f"Référentiel chargé : {Region.objects.count()} régions, "
            f"{Prefecture.objects.count()} préfectures, {Commune.objects.count()} communes ({nb} nouvelles)."
        ))
