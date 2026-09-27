from django.contrib import admin

from .models import Commune, Prefecture, Quartier, Region


class PrefectureInline(admin.TabularInline):
    model = Prefecture
    extra = 0


class CommuneInline(admin.TabularInline):
    model = Commune
    extra = 0


class QuartierInline(admin.TabularInline):
    model = Quartier
    extra = 0


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ["nom", "code", "actif"]
    search_fields = ["nom", "code"]
    inlines = [PrefectureInline]


@admin.register(Prefecture)
class PrefectureAdmin(admin.ModelAdmin):
    list_display = ["nom", "region", "code", "actif"]
    list_filter = ["region", "actif"]
    search_fields = ["nom", "code"]
    inlines = [CommuneInline]


@admin.register(Commune)
class CommuneAdmin(admin.ModelAdmin):
    list_display = ["nom", "prefecture", "code", "actif"]
    list_filter = ["prefecture__region", "actif"]
    search_fields = ["nom", "code", "prefecture__nom"]
    list_select_related = ["prefecture"]
    inlines = [QuartierInline]


@admin.register(Quartier)
class QuartierAdmin(admin.ModelAdmin):
    list_display = ["nom", "commune", "actif"]
    list_filter = ["commune__prefecture__region", "actif"]
    search_fields = ["nom", "commune__nom"]
    autocomplete_fields = ["commune"]
