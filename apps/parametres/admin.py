from django.contrib import admin

from .models import ParametreSysteme


@admin.register(ParametreSysteme)
class ParametreSystemeAdmin(admin.ModelAdmin):
    fieldsets = [
        ("Contrôle des passeports", {"fields": [
            "validite_min_mois", "marge_alerte_mois", "date_reference",
            "bloquer_passeport_expire", "bloquer_passeport_non_conforme",
        ]}),
        ("Badges", {"fields": ["afficher_passeport_sur_badge"]}),
    ]

    def has_add_permission(self, request):
        return not ParametreSysteme.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
