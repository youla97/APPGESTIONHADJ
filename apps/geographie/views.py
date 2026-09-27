"""Points d'accès JSON pour les listes déroulantes en cascade."""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from .models import Commune, Prefecture, Quartier


def _options(qs):
    return JsonResponse({"options": [{"id": o.pk, "nom": o.nom} for o in qs.filter(actif=True)]})


@login_required
def prefectures(request):
    return _options(Prefecture.objects.filter(region_id=request.GET.get("region") or 0))


@login_required
def communes(request):
    return _options(Commune.objects.filter(prefecture_id=request.GET.get("prefecture") or 0))


@login_required
def quartiers(request):
    return _options(Quartier.objects.filter(commune_id=request.GET.get("commune") or 0))
