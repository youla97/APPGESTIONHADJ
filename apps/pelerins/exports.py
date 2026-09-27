"""Exports Excel, CSV et PDF des listes de pèlerins (§16)."""
import csv
import io

from django.http import HttpResponse
from django.utils import timezone

from .services import evaluer_passeport, seuils_passeport

COLONNES = [
    "Matricule", "Nom", "Prénom(s)", "Sexe", "Date de naissance", "Téléphone",
    "Région", "Préfecture", "Commune", "Quartier",
    "N° passeport", "Expiration", "Statut passeport", "N° dossier", "Année", "Statut dossier", "Complétude %",
]


def lignes(pelerins):
    seuils = seuils_passeport()
    for p in pelerins.select_related("commune__prefecture__region", "quartier").prefetch_related(
        "passeports", "dossiers__campagne"
    ):
        passeport = next((x for x in p.passeports.all() if x.est_actif and not x.est_supprime), None)
        dossier = next((d for d in p.dossiers.all() if not d.est_supprime), None)
        commune = p.commune
        yield [
            p.matricule, p.nom, p.prenoms, p.get_sexe_display(), p.date_naissance.strftime("%d/%m/%Y"),
            p.telephone_principal, commune.prefecture.region.nom, commune.prefecture.nom, commune.nom,
            p.quartier.nom if p.quartier else p.localite,
            passeport.numero if passeport else "",
            passeport.date_expiration.strftime("%d/%m/%Y") if passeport else "",
            evaluer_passeport(passeport.date_expiration, seuils).label if passeport else "",
            dossier.numero if dossier else "", dossier.campagne.annee if dossier else "",
            dossier.get_statut_display() if dossier else "", dossier.taux_completude if dossier else "",
        ]


def _nom_fichier(ext):
    return f"pelerins_{timezone.localtime():%Y%m%d_%H%M}.{ext}"


def export_csv(pelerins):
    reponse = HttpResponse(content_type="text/csv; charset=utf-8")
    reponse["Content-Disposition"] = f'attachment; filename="{_nom_fichier("csv")}"'
    reponse.write("﻿")  # BOM pour ouverture correcte dans Excel
    ecrivain = csv.writer(reponse, delimiter=";")
    ecrivain.writerow(COLONNES)
    ecrivain.writerows(lignes(pelerins))
    return reponse


def export_excel(pelerins, titre="Liste des pèlerins"):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter

    classeur = Workbook()
    feuille = classeur.active
    feuille.title = "Pèlerins"
    feuille.append([titre])
    feuille["A1"].font = Font(bold=True, size=14)
    feuille.append([f"Généré le {timezone.localtime():%d/%m/%Y à %H:%M}"])
    feuille.append([])
    feuille.append(COLONNES)
    for cellule in feuille[4]:
        cellule.font = Font(bold=True, color="FFFFFF")
        cellule.fill = PatternFill("solid", fgColor="0B6E4F")
    for ligne in lignes(pelerins):
        feuille.append(ligne)
    for i, _ in enumerate(COLONNES, start=1):
        feuille.column_dimensions[get_column_letter(i)].width = 16
    feuille.freeze_panes = "A5"
    feuille.auto_filter.ref = f"A4:{get_column_letter(len(COLONNES))}{feuille.max_row}"

    tampon = io.BytesIO()
    classeur.save(tampon)
    reponse = HttpResponse(
        tampon.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    reponse["Content-Disposition"] = f'attachment; filename="{_nom_fichier("xlsx")}"'
    return reponse


def export_pdf(pelerins, titre="Liste des pèlerins"):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    colonnes_pdf = [0, 1, 2, 3, 4, 5, 8, 10, 11, 12, 13, 15]  # sous-ensemble lisible en paysage
    donnees = [[COLONNES[i] for i in colonnes_pdf]]
    donnees += [[str(ligne[i]) for i in colonnes_pdf] for ligne in lignes(pelerins)]

    tampon = io.BytesIO()
    doc = SimpleDocTemplate(tampon, pagesize=landscape(A4), leftMargin=1 * cm, rightMargin=1 * cm,
                            topMargin=1 * cm, bottomMargin=1 * cm, title=titre)
    styles = getSampleStyleSheet()
    tableau = Table(donnees, repeatRows=1)
    tableau.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B6E4F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F5F3")]),
    ]))
    doc.build([
        Paragraph("République de Guinée – " + titre, styles["Title"]),
        Paragraph(f"Généré le {timezone.localtime():%d/%m/%Y à %H:%M} – {len(donnees) - 1} pèlerin(s)",
                  styles["Normal"]),
        Spacer(1, 0.4 * cm),
        tableau,
    ])
    reponse = HttpResponse(tampon.getvalue(), content_type="application/pdf")
    reponse["Content-Disposition"] = f'attachment; filename="{_nom_fichier("pdf")}"'
    return reponse
