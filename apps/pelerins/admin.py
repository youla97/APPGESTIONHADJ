from django.contrib import admin

from .models import Agence, CampagneHadj, Document, DossierHadj, Groupe, Passeport, Pelerin, SignalementDoublon


class PasseportInline(admin.TabularInline):
    model = Passeport
    extra = 0
    fields = ["numero", "date_delivrance", "date_expiration", "pays_delivrance", "est_actif", "scan"]


class DossierInline(admin.TabularInline):
    model = DossierHadj
    fk_name = "pelerin"
    extra = 0
    fields = ["campagne", "passeport", "agence", "groupe", "statut", "statut_pelerin"]


@admin.register(Pelerin)
class PelerinAdmin(admin.ModelAdmin):
    list_display = ["matricule", "nom", "prenom1", "sexe", "date_naissance", "telephone_principal", "commune"]
    list_filter = ["sexe", "commune__prefecture__region"]
    search_fields = ["matricule", "nom", "prenom1", "prenom2", "telephone_principal", "passeports__numero"]
    autocomplete_fields = ["commune", "quartier"]
    readonly_fields = ["matricule", "uuid", "cree_le", "cree_par", "modifie_le", "modifie_par"]
    inlines = [PasseportInline, DossierInline]


@admin.register(Passeport)
class PasseportAdmin(admin.ModelAdmin):
    list_display = ["numero", "pelerin", "date_delivrance", "date_expiration", "est_actif"]
    search_fields = ["numero", "pelerin__nom"]
    raw_id_fields = ["pelerin"]


@admin.register(DossierHadj)
class DossierHadjAdmin(admin.ModelAdmin):
    list_display = ["numero", "pelerin", "campagne", "statut", "statut_pelerin", "taux_completude", "groupe"]
    list_filter = ["campagne", "statut", "statut_pelerin", "agence"]
    search_fields = ["numero", "pelerin__nom", "pelerin__prenom1"]
    raw_id_fields = ["pelerin", "passeport"]


@admin.register(CampagneHadj)
class CampagneHadjAdmin(admin.ModelAdmin):
    list_display = ["annee", "libelle", "date_depart_prevue", "date_retour_prevue", "quota", "est_active"]


@admin.register(Agence)
class AgenceAdmin(admin.ModelAdmin):
    list_display = ["nom", "sigle", "numero_agrement", "telephone", "actif"]
    search_fields = ["nom", "sigle"]


@admin.register(Groupe)
class GroupeAdmin(admin.ModelAdmin):
    list_display = ["nom", "code", "campagne", "agence", "encadreur"]
    list_filter = ["campagne", "agence"]


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["pelerin", "type_document", "libelle", "cree_le"]
    list_filter = ["type_document"]
    raw_id_fields = ["pelerin", "dossier"]


@admin.register(SignalementDoublon)
class SignalementDoublonAdmin(admin.ModelAdmin):
    list_display = ["pelerin", "pelerin_similaire", "critere", "score", "decision", "traite_par"]
    list_filter = ["decision", "critere"]
    raw_id_fields = ["pelerin", "pelerin_similaire"]
