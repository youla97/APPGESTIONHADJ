from django.contrib import admin

from .models import Badge, VerificationBadge


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ["dossier", "est_actif", "nb_impressions", "derniere_impression", "derniere_verification", "cree_le"]
    list_filter = ["est_actif", "dossier__campagne"]
    search_fields = ["dossier__numero", "dossier__pelerin__nom", "jeton"]
    raw_id_fields = ["dossier"]


@admin.register(VerificationBadge)
class VerificationBadgeAdmin(admin.ModelAdmin):
    list_display = ["date", "resultat", "badge", "controleur", "lieu", "adresse_ip"]
    list_filter = ["resultat", "date"]
    search_fields = ["jeton_scanne", "badge__dossier__numero"]

    def has_change_permission(self, request, obj=None):
        return False
