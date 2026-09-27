from django.urls import path

from . import views

app_name = "pelerins"

urlpatterns = [
    path("", views.liste, name="liste"),
    path("nouveau/", views.creer, name="creer"),
    path("<int:pk>/", views.detail, name="detail"),
    path("<int:pk>/modifier/", views.modifier, name="modifier"),
    path("<int:pk>/supprimer/", views.supprimer, name="supprimer"),
    path("dossiers/<int:pk>/valider/", views.valider_dossier, name="valider_dossier"),
    path("controle-passeport/", views.controle_passeport, name="controle_passeport"),
    path("doublons/", views.doublons, name="doublons"),
    path("doublons/<int:pk>/traiter/", views.traiter_doublon, name="traiter_doublon"),
]
