from django.urls import path

from . import views

app_name = "badges"

urlpatterns = [
    path("", views.liste, name="liste"),
    path("generer/<int:dossier_pk>/", views.generer, name="generer"),
    path("<int:pk>/", views.imprimer, name="imprimer"),
    path("<int:pk>/qr.png", views.qr_code, name="qr"),
    path("controle/", views.scanner, name="scanner"),
    path("v/<str:jeton>/", views.verifier, name="verifier"),
]
