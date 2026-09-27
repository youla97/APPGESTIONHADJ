from django.urls import path

from . import views

app_name = "geographie"

urlpatterns = [
    path("prefectures/", views.prefectures, name="prefectures"),
    path("communes/", views.communes, name="communes"),
    path("quartiers/", views.quartiers, name="quartiers"),
]
