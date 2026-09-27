"""
Modèles métier : campagne Hadj, agence, groupe, pèlerin, passeport,
dossier Hadj, documents et signalements de doublons (§7 à §13, §21, §22).

Chaîne : Région → Préfecture → Commune → Quartier → Pèlerin → Dossier Hadj → Passeport → Badge.
Le numéro de passeport est l'identifiant MÉTIER unique ; la clé primaire
reste un identifiant technique interne (§31).
"""
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.core.models import Horodatage, SuppressionLogique

from .statuts import StatutDossier, StatutPasseport, StatutPelerin


# --- Validation des fichiers joints (§13) -------------------------------------

def valider_taille_fichier(fichier):
    limite = settings.DOCUMENTS_TAILLE_MAX_MO * 1024 * 1024
    if fichier.size > limite:
        raise ValidationError(f"Fichier trop volumineux (maximum {settings.DOCUMENTS_TAILLE_MAX_MO} Mo).")


VALIDATEURS_DOCUMENT = [FileExtensionValidator(settings.DOCUMENTS_EXTENSIONS), valider_taille_fichier]
VALIDATEURS_IMAGE = [FileExtensionValidator(["jpg", "jpeg", "png"]), valider_taille_fichier]


def _chemin(sous_dossier, nom_fichier):
    """Nom de fichier aléatoire : on n'expose jamais le nom d'origine ni l'identité."""
    ext = nom_fichier.rsplit(".", 1)[-1].lower()
    return f"{sous_dossier}/{timezone.now():%Y/%m}/{uuid.uuid4().hex}.{ext}"


def chemin_photo(instance, nom_fichier):
    return _chemin("photos", nom_fichier)


def chemin_scan_passeport(instance, nom_fichier):
    return _chemin("passeports", nom_fichier)


def chemin_document(instance, nom_fichier):
    return _chemin("documents", nom_fichier)


def normaliser_numero_passeport(numero):
    return "".join((numero or "").split()).upper()


# --- Référentiels Hadj --------------------------------------------------------

class CampagneHadj(models.Model):
    """Une campagne par année (§22 : Hadj 2026, 2027, …)."""

    annee = models.PositiveSmallIntegerField("année", unique=True)
    libelle = models.CharField("libellé", max_length=100, blank=True)
    date_ouverture = models.DateField("ouverture des inscriptions", null=True, blank=True)
    date_cloture = models.DateField("clôture des inscriptions", null=True, blank=True)
    date_depart_prevue = models.DateField("date de départ prévue", null=True, blank=True)
    date_retour_prevue = models.DateField("date de retour prévue", null=True, blank=True)
    quota = models.PositiveIntegerField("quota", null=True, blank=True)
    est_active = models.BooleanField("campagne en cours", default=False)

    class Meta:
        verbose_name = "campagne Hadj"
        verbose_name_plural = "campagnes Hadj"
        ordering = ["-annee"]

    def __str__(self):
        return self.libelle or f"Hadj {self.annee}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.est_active:
            CampagneHadj.objects.exclude(pk=self.pk).update(est_active=False)

    @classmethod
    def active(cls):
        return cls.objects.filter(est_active=True).first() or cls.objects.first()


class Agence(models.Model):
    """Agence ou structure d'encadrement."""

    nom = models.CharField("nom", max_length=150, unique=True)
    sigle = models.CharField("sigle", max_length=30, blank=True)
    numero_agrement = models.CharField("n° d'agrément", max_length=50, blank=True)
    telephone = models.CharField("téléphone", max_length=30, blank=True)
    email = models.EmailField("e-mail", blank=True)
    adresse = models.CharField("adresse", max_length=255, blank=True)
    actif = models.BooleanField("actif", default=True)

    class Meta:
        verbose_name = "agence / structure d'encadrement"
        verbose_name_plural = "agences / structures d'encadrement"
        ordering = ["nom"]

    def __str__(self):
        return self.sigle or self.nom


class Groupe(models.Model):
    campagne = models.ForeignKey(CampagneHadj, verbose_name="campagne", on_delete=models.PROTECT, related_name="groupes")
    agence = models.ForeignKey(Agence, verbose_name="agence", on_delete=models.SET_NULL, null=True, blank=True)
    code = models.CharField("code", max_length=20, blank=True)
    nom = models.CharField("nom", max_length=100)
    encadreur = models.CharField("encadreur", max_length=150, blank=True)
    telephone_encadreur = models.CharField("téléphone de l'encadreur", max_length=30, blank=True)

    class Meta:
        verbose_name = "groupe"
        ordering = ["campagne", "nom"]
        constraints = [models.UniqueConstraint(fields=["campagne", "nom"], name="groupe_nom_unique_par_campagne")]

    def __str__(self):
        return f"{self.nom} ({self.campagne.annee})"


# --- Pèlerin ------------------------------------------------------------------

class Pelerin(Horodatage, SuppressionLogique):
    class Sexe(models.TextChoices):
        MASCULIN = "M", "Masculin"
        FEMININ = "F", "Féminin"

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    matricule = models.CharField("n° d'identification", max_length=20, unique=True, editable=False, blank=True)

    # Identification
    nom = models.CharField("nom", max_length=100, db_index=True)
    prenom1 = models.CharField("prénom 1", max_length=100, db_index=True)
    prenom2 = models.CharField("prénom 2", max_length=100, blank=True)
    sexe = models.CharField("sexe", max_length=1, choices=Sexe.choices)
    date_naissance = models.DateField("date de naissance", db_index=True)
    lieu_naissance = models.CharField("lieu de naissance", max_length=150)
    nationalite = models.CharField("nationalité", max_length=60, default="Guinéenne")
    photo = models.ImageField("photo", upload_to=chemin_photo, blank=True, validators=VALIDATEURS_IMAGE)

    # Coordonnées
    telephone_principal = models.CharField("téléphone principal", max_length=30, db_index=True)
    telephone_secondaire = models.CharField("téléphone secondaire", max_length=30, blank=True)
    adresse = models.CharField("adresse", max_length=255, blank=True)
    commune = models.ForeignKey(
        "geographie.Commune", verbose_name="commune", on_delete=models.PROTECT, related_name="pelerins"
    )
    quartier = models.ForeignKey(
        "geographie.Quartier", verbose_name="quartier / district", on_delete=models.PROTECT,
        null=True, blank=True, related_name="pelerins",
    )
    localite = models.CharField("localité", max_length=150, blank=True)

    observations = models.TextField("observations", blank=True)

    class Meta:
        verbose_name = "pèlerin"
        ordering = ["nom", "prenom1"]
        indexes = [models.Index(fields=["nom", "prenom1", "date_naissance"], name="pelerin_identite_idx")]

    def __str__(self):
        return self.nom_complet

    def clean(self):
        if self.quartier_id and self.commune_id and self.quartier.commune_id != self.commune_id:
            raise ValidationError({"quartier": "Ce quartier n'appartient pas à la commune choisie."})
        if self.date_naissance and self.date_naissance > timezone.localdate():
            raise ValidationError({"date_naissance": "La date de naissance est dans le futur."})

    def save(self, *args, **kwargs):
        self.nom = self.nom.strip().upper()
        self.prenom1 = self.prenom1.strip().title()
        self.prenom2 = self.prenom2.strip().title()
        super().save(*args, **kwargs)
        if not self.matricule:
            self.matricule = f"PEL-{self.pk:07d}"
            Pelerin.tous.filter(pk=self.pk).update(matricule=self.matricule)

    @property
    def prenoms(self):
        return " ".join(p for p in [self.prenom1, self.prenom2] if p)

    @property
    def nom_complet(self):
        return f"{self.prenoms} {self.nom}".strip()

    @property
    def age(self):
        if not self.date_naissance:
            return None
        auj = timezone.localdate()
        return auj.year - self.date_naissance.year - (
            (auj.month, auj.day) < (self.date_naissance.month, self.date_naissance.day)
        )

    @property
    def passeport_actif(self):
        return self.passeports.filter(est_actif=True).order_by("-date_expiration").first()


# --- Passeport ----------------------------------------------------------------

class Passeport(Horodatage, SuppressionLogique):
    pelerin = models.ForeignKey(Pelerin, verbose_name="pèlerin", on_delete=models.PROTECT, related_name="passeports")
    numero = models.CharField("numéro de passeport", max_length=30, db_index=True)
    date_delivrance = models.DateField("date de délivrance")
    date_expiration = models.DateField("date d'expiration", db_index=True)
    autorite_delivrance = models.CharField("autorité de délivrance", max_length=150, blank=True)
    pays_delivrance = models.CharField("pays de délivrance", max_length=60, default="Guinée")
    scan = models.FileField(
        "scan / photo du passeport", upload_to=chemin_scan_passeport, blank=True, validators=VALIDATEURS_DOCUMENT
    )
    est_actif = models.BooleanField("passeport en cours d'utilisation", default=True)

    class Meta:
        verbose_name = "passeport"
        ordering = ["-date_expiration"]
        constraints = [
            # Contrôle principal des doublons (§8, §10)
            models.UniqueConstraint(
                fields=["numero"], condition=Q(est_supprime=False), name="passeport_numero_unique"
            ),
        ]

    def __str__(self):
        return self.numero

    def clean(self):
        self.numero = normaliser_numero_passeport(self.numero)
        if self.date_delivrance and self.date_expiration and self.date_expiration <= self.date_delivrance:
            raise ValidationError({"date_expiration": "La date d'expiration doit suivre la date de délivrance."})

    def save(self, *args, **kwargs):
        self.numero = normaliser_numero_passeport(self.numero)
        super().save(*args, **kwargs)

    @property
    def statut(self) -> StatutPasseport:
        from .services import evaluer_passeport
        return evaluer_passeport(self.date_expiration)


# --- Dossier Hadj (un par pèlerin et par campagne) ---------------------------

class DossierHadj(Horodatage, SuppressionLogique):
    numero = models.CharField("n° de dossier", max_length=30, unique=True, editable=False, blank=True)
    pelerin = models.ForeignKey(Pelerin, verbose_name="pèlerin", on_delete=models.PROTECT, related_name="dossiers")
    campagne = models.ForeignKey(
        CampagneHadj, verbose_name="campagne", on_delete=models.PROTECT, related_name="dossiers"
    )
    passeport = models.ForeignKey(
        Passeport, verbose_name="passeport utilisé", on_delete=models.PROTECT,
        null=True, blank=True, related_name="dossiers",
    )
    agence = models.ForeignKey(Agence, verbose_name="agence", on_delete=models.SET_NULL, null=True, blank=True)
    groupe = models.ForeignKey(Groupe, verbose_name="groupe", on_delete=models.SET_NULL, null=True, blank=True)
    statut = models.CharField(
        "statut du dossier", max_length=20, choices=StatutDossier.choices, default=StatutDossier.INCOMPLET,
        db_index=True,
    )
    statut_pelerin = models.CharField(
        "statut du pèlerin", max_length=20, choices=StatutPelerin.choices, default=StatutPelerin.INSCRIT,
        db_index=True,
    )
    taux_completude = models.PositiveSmallIntegerField("taux de complétude (%)", default=0, editable=False)
    observations = models.TextField("observations", blank=True)
    valide_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="validé par", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+", editable=False,
    )
    valide_le = models.DateTimeField("validé le", null=True, blank=True, editable=False)

    class Meta:
        verbose_name = "dossier Hadj"
        verbose_name_plural = "dossiers Hadj"
        ordering = ["-campagne__annee", "pelerin__nom"]
        constraints = [
            models.UniqueConstraint(
                fields=["pelerin", "campagne"], condition=Q(est_supprime=False),
                name="dossier_unique_par_campagne",
            ),
        ]

    def __str__(self):
        return f"{self.numero} – {self.pelerin}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.numero:
            self.numero = f"H{self.campagne.annee}-{self.pk:06d}"
            DossierHadj.tous.filter(pk=self.pk).update(numero=self.numero)

    # §18 — Détection des informations manquantes
    def controles_completude(self):
        """Liste de (rubrique, fournie ?) servant au calcul de complétude."""
        p = self.pelerin
        types_fournis = set(p.documents.values_list("type_document", flat=True))
        controles = [
            ("Photo d'identité", bool(p.photo)),
            ("Lieu de naissance", bool(p.lieu_naissance)),
            ("Téléphone principal", bool(p.telephone_principal)),
            ("Quartier ou localité", bool(p.quartier_id or p.localite)),
            ("Passeport", bool(self.passeport_id)),
            ("Scan du passeport", bool(self.passeport_id and self.passeport.scan)),
        ]
        controles += [(Document.Type(t).label, t in types_fournis) for t in Document.TYPES_OBLIGATOIRES]
        return controles

    def elements_manquants(self):
        return [rubrique for rubrique, ok in self.controles_completude() if not ok]

    def calculer_completude(self, enregistrer=True):
        controles = self.controles_completude()
        manquants = [rubrique for rubrique, ok in controles if not ok]
        self.taux_completude = round(100 * (len(controles) - len(manquants)) / len(controles))
        if self.statut in (StatutDossier.INCOMPLET, StatutDossier.COMPLET):
            self.statut = StatutDossier.COMPLET if not manquants else StatutDossier.INCOMPLET
        if enregistrer and self.pk:
            DossierHadj.tous.filter(pk=self.pk).update(taux_completude=self.taux_completude, statut=self.statut)
        return manquants


# --- Documents (§13) ----------------------------------------------------------

class Document(Horodatage, SuppressionLogique):
    class Type(models.TextChoices):
        PHOTO = "PHOTO", "Photo"
        PASSEPORT = "PASSEPORT", "Passeport"
        ACTE_NAISSANCE = "ACTE_NAISSANCE", "Extrait d'acte de naissance"
        CERTIFICAT_MEDICAL = "CERTIFICAT_MEDICAL", "Certificat médical"
        CARNET_VACCINATION = "CARNET_VACCINATION", "Carnet de vaccination"
        RECU_PAIEMENT = "RECU_PAIEMENT", "Reçu de paiement"
        AUTRE = "AUTRE", "Autre pièce"

    # Pièces exigées pour un dossier complet (à ajuster selon la réglementation)
    TYPES_OBLIGATOIRES = [Type.CERTIFICAT_MEDICAL, Type.CARNET_VACCINATION]

    pelerin = models.ForeignKey(Pelerin, verbose_name="pèlerin", on_delete=models.PROTECT, related_name="documents")
    dossier = models.ForeignKey(
        DossierHadj, verbose_name="dossier", on_delete=models.PROTECT, null=True, blank=True, related_name="documents"
    )
    type_document = models.CharField("type de document", max_length=30, choices=Type.choices)
    libelle = models.CharField("libellé", max_length=150, blank=True)
    fichier = models.FileField("fichier", upload_to=chemin_document, validators=VALIDATEURS_DOCUMENT)

    class Meta:
        verbose_name = "document"
        ordering = ["-cree_le"]

    def __str__(self):
        return self.libelle or self.get_type_document_display()

    @property
    def est_image(self):
        return self.fichier.name.lower().endswith((".jpg", ".jpeg", ".png"))


# --- Doublons (§10) -----------------------------------------------------------

class SignalementDoublon(Horodatage):
    class Critere(models.TextChoices):
        PASSEPORT = "PASSEPORT", "Numéro de passeport"
        IDENTITE = "IDENTITE", "Nom, prénom et date de naissance"
        TELEPHONE = "TELEPHONE", "Téléphone"
        COMBINAISON = "COMBINAISON", "Combinaison de critères"

    class Decision(models.TextChoices):
        A_TRAITER = "A_TRAITER", "À traiter"
        CONFIRME = "CONFIRME", "Doublon confirmé"
        CONSERVE = "CONSERVE", "Dossiers conservés (justifié)"
        FUSIONNE = "FUSIONNE", "Fusionné"

    pelerin = models.ForeignKey(Pelerin, on_delete=models.CASCADE, related_name="doublons_signales")
    pelerin_similaire = models.ForeignKey(Pelerin, on_delete=models.CASCADE, related_name="+")
    critere = models.CharField("critère", max_length=20, choices=Critere.choices)
    score = models.PositiveSmallIntegerField("score de similarité", default=0)
    decision = models.CharField(
        "décision", max_length=20, choices=Decision.choices, default=Decision.A_TRAITER, db_index=True
    )
    justification = models.TextField("justification", blank=True)
    traite_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    traite_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "signalement de doublon"
        verbose_name_plural = "signalements de doublons"
        ordering = ["decision", "-score"]
        constraints = [
            models.UniqueConstraint(fields=["pelerin", "pelerin_similaire"], name="doublon_paire_unique"),
        ]

    def __str__(self):
        return f"{self.pelerin} ≈ {self.pelerin_similaire}"
