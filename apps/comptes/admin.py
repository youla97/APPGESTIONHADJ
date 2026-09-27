from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Utilisateur


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    list_display = ["username", "last_name", "first_name", "role", "region", "prefecture", "commune", "is_active"]
    list_filter = ["role", "is_active", "region"]
    search_fields = ["username", "first_name", "last_name", "email", "telephone"]
    autocomplete_fields = ["commune"]
    fieldsets = UserAdmin.fieldsets + (
        ("Rôle et périmètre", {"fields": ("role", "fonction", "telephone", "region", "prefecture", "commune")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Rôle et périmètre", {"fields": ("first_name", "last_name", "role", "region", "prefecture", "commune")}),
    )
