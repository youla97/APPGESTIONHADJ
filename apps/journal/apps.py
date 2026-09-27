from django.apps import AppConfig, apps


class JournalConfig(AppConfig):
    name = "apps.journal"
    verbose_name = "Journal et traçabilité"

    def ready(self):
        from .signals import suivre

        for label in [
            "pelerins.Pelerin", "pelerins.Passeport", "pelerins.DossierHadj", "pelerins.Document",
            "pelerins.SignalementDoublon", "badges.Badge", "parametres.ParametreSysteme", "comptes.Utilisateur",
        ]:
            suivre(apps.get_model(label))
