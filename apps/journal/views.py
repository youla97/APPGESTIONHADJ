from django.core.paginator import Paginator
from django.shortcuts import render

from apps.comptes.mixins import permission_metier
from apps.comptes.roles import Perm

from .models import Historique, JournalConnexion


@permission_metier(Perm.JOURNAL_VOIR)
def historique(request):
    entrees = Historique.objects.select_related("utilisateur", "content_type")
    action = request.GET.get("action")
    if action:
        entrees = entrees.filter(action=action)
    q = request.GET.get("q", "").strip()
    if q:
        entrees = entrees.filter(objet_repr__icontains=q)
    return render(request, "journal/historique.html", {
        "page": Paginator(entrees, 50).get_page(request.GET.get("page")),
        "actions": Historique.Action.choices, "action": action, "q": q,
    })


@permission_metier(Perm.JOURNAL_VOIR)
def connexions(request):
    return render(request, "journal/connexions.html", {
        "page": Paginator(JournalConnexion.objects.select_related("utilisateur"), 50).get_page(request.GET.get("page")),
    })
