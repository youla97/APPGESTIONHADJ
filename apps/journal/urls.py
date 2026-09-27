from django.urls import path

from . import views

app_name = "journal"

urlpatterns = [
    path("", views.historique, name="historique"),
    path("connexions/", views.connexions, name="connexions"),
]
