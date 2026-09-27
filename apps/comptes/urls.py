from django.contrib.auth import views as auth_views
from django.urls import path

urlpatterns = [
    path("connexion/", auth_views.LoginView.as_view(redirect_authenticated_user=True), name="login"),
    path("deconnexion/", auth_views.LogoutView.as_view(), name="logout"),
    path("mot-de-passe/", auth_views.PasswordChangeView.as_view(), name="password_change"),
    path("mot-de-passe/ok/", auth_views.PasswordChangeDoneView.as_view(), name="password_change_done"),
]
