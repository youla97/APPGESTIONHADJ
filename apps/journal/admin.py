from django.contrib import admin

from .models import Historique, JournalConnexion


class LectureSeuleAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Historique)
class HistoriqueAdmin(LectureSeuleAdmin):
    list_display = ["date", "utilisateur", "action", "content_type", "objet_repr", "adresse_ip"]
    list_filter = ["action", "content_type", "date"]
    search_fields = ["objet_repr", "details", "utilisateur__username"]
    date_hierarchy = "date"


@admin.register(JournalConnexion)
class JournalConnexionAdmin(LectureSeuleAdmin):
    list_display = ["date", "evenement", "identifiant_saisi", "utilisateur", "adresse_ip"]
    list_filter = ["evenement", "date"]
    search_fields = ["identifiant_saisi", "adresse_ip"]
    date_hierarchy = "date"
