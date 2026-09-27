from django.conf import settings


def application(request):
    return {
        "APPLICATION_NOM": settings.APPLICATION_NOM,
        "APPLICATION_PAYS": settings.APPLICATION_PAYS,
    }
