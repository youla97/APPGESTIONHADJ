import io

import qrcode
from django.urls import reverse


def url_verification(request, badge):
    return request.build_absolute_uri(reverse("badges:verifier", args=[badge.jeton]))


def qr_png(contenu: str, taille_case=8) -> bytes:
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=taille_case, border=2)
    qr.add_data(contenu)
    qr.make(fit=True)
    tampon = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(tampon, format="PNG")
    return tampon.getvalue()
