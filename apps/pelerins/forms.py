from django import forms

from apps.geographie.models import Commune, Prefecture, Quartier, Region

from .models import CampagneHadj, Document, DossierHadj, Groupe, Passeport, Pelerin
from .services import controler_passeport
from .statuts import StatutDossier, StatutPasseport


class DateInput(forms.DateInput):
    input_type = "date"

    def __init__(self, **kwargs):
        super().__init__(format="%Y-%m-%d", **kwargs)


class FormulaireBootstrap:
    """Ajoute les classes Bootstrap à tous les widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for champ in self.fields.values():
            w = champ.widget
            if isinstance(w, (forms.Select, forms.SelectMultiple)):
                w.attrs.setdefault("class", "form-select")
            elif isinstance(w, forms.CheckboxInput):
                w.attrs.setdefault("class", "form-check-input")
            else:
                w.attrs.setdefault("class", "form-control")


class PelerinForm(FormulaireBootstrap, forms.ModelForm):
    region = forms.ModelChoiceField(Region.objects.filter(actif=True), label="Région", required=False)
    prefecture = forms.ModelChoiceField(Prefecture.objects.filter(actif=True), label="Préfecture", required=False)

    class Meta:
        model = Pelerin
        fields = [
            "nom", "prenom1", "prenom2", "sexe", "date_naissance", "lieu_naissance", "nationalite", "photo",
            "telephone_principal", "telephone_secondaire", "adresse",
            "region", "prefecture", "commune", "quartier", "localite", "observations",
        ]
        widgets = {"date_naissance": DateInput(), "observations": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, utilisateur=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["commune"].queryset = Commune.objects.filter(actif=True).select_related("prefecture")
        self.fields["quartier"].queryset = Quartier.objects.filter(actif=True)
        if self.instance.pk and self.instance.commune_id:
            self.initial.setdefault("prefecture", self.instance.commune.prefecture_id)
            self.initial.setdefault("region", self.instance.commune.prefecture.region_id)
        # Un agent communal n'enregistre que dans sa commune
        if utilisateur is not None and not utilisateur.est_admin_national:
            self.fields["commune"].queryset = self._communes_perimetre(utilisateur)

    @staticmethod
    def _communes_perimetre(utilisateur):
        qs = Commune.objects.filter(actif=True)
        if utilisateur.commune_id:
            return qs.filter(pk=utilisateur.commune_id)
        if utilisateur.prefecture_id:
            return qs.filter(prefecture_id=utilisateur.prefecture_id)
        if utilisateur.region_id:
            return qs.filter(prefecture__region_id=utilisateur.region_id)
        return qs


class PasseportForm(FormulaireBootstrap, forms.ModelForm):
    class Meta:
        model = Passeport
        fields = ["numero", "date_delivrance", "date_expiration", "autorite_delivrance", "pays_delivrance", "scan"]
        widgets = {"date_delivrance": DateInput(), "date_expiration": DateInput()}

    def __init__(self, *args, pelerin_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.pelerin_id = pelerin_id
        self.controle = None
        self.fields["numero"].widget.attrs.update({"autocomplete": "off", "data-controle-passeport": "1"})

    def clean(self):
        donnees = super().clean()
        numero = donnees.get("numero")
        if numero:
            self.controle = controler_passeport(
                numero, donnees.get("date_expiration"), exclure_pelerin_id=self.pelerin_id
            )
            # Le doublon empêche l'enregistrement ; un passeport expiré / non conforme
            # n'empêche pas la saisie mais bloque le dossier selon le paramétrage (voir views.creer).
            for alerte in self.controle.alertes:
                if alerte["titre"] == "DOUBLON DÉTECTÉ":
                    self.add_error("numero", f"{alerte['titre']} : {alerte['message']}")
        return donnees

    def validate_unique(self):
        # Le doublon est déjà signalé avec un message explicite dans clean()
        if self.controle and self.controle.doublon:
            return
        super().validate_unique()


class DossierHadjForm(FormulaireBootstrap, forms.ModelForm):
    class Meta:
        model = DossierHadj
        fields = ["campagne", "agence", "groupe", "statut_pelerin", "observations"]
        widgets = {"observations": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["campagne"].initial = CampagneHadj.active()
        self.fields["groupe"].queryset = Groupe.objects.select_related("campagne")


class DocumentForm(FormulaireBootstrap, forms.ModelForm):
    class Meta:
        model = Document
        fields = ["type_document", "libelle", "fichier"]


class RechercheForm(FormulaireBootstrap, forms.Form):
    """Recherche avancée, critères combinables (§11)."""

    q = forms.CharField(label="Recherche", required=False,
                        widget=forms.TextInput(attrs={"placeholder": "Nom, prénom, passeport, téléphone, n° dossier…"}))
    region = forms.ModelChoiceField(Region.objects.all(), label="Région", required=False)
    prefecture = forms.ModelChoiceField(Prefecture.objects.all(), label="Préfecture", required=False)
    commune = forms.ModelChoiceField(Commune.objects.all(), label="Commune", required=False)
    quartier = forms.ModelChoiceField(Quartier.objects.all(), label="Quartier", required=False)
    campagne = forms.ModelChoiceField(CampagneHadj.objects.all(), label="Année Hadj", required=False)
    groupe = forms.ModelChoiceField(Groupe.objects.all(), label="Groupe", required=False)
    statut_dossier = forms.ChoiceField(label="Statut du dossier", required=False,
                                       choices=[("", "---------")] + StatutDossier.choices)
    statut_passeport = forms.ChoiceField(label="Statut du passeport", required=False,
                                         choices=[("", "---------")] + StatutPasseport.choices)
    sexe = forms.ChoiceField(label="Sexe", required=False, choices=[("", "---------")] + Pelerin.Sexe.choices)
