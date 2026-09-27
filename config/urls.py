from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Administration – Gestion des Pèlerins (Hadj)"
admin.site.site_title = "Pèlerins Hadj"
admin.site.index_title = "Référentiels et paramétrage"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("comptes/", include("apps.comptes.urls")),
    path("pelerins/", include("apps.pelerins.urls")),
    path("badges/", include("apps.badges.urls")),
    path("journal/", include("apps.journal.urls")),
    path("geographie/", include("apps.geographie.urls")),
    path("", include("apps.core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
