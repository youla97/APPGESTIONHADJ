# Gestion des Pèlerins – Hadj (République de Guinée)

Application web nationale de gestion des pèlerins : enregistrement, contrôle des passeports,
détection des doublons, badges QR Code, recherche, exports, statistiques et traçabilité.
Développée en **Python / Django 5.2 (LTS)**.

## Démarrage rapide (développement)

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (Linux : source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env            # puis renseigner SECRET_KEY
python manage.py migrate
python manage.py charger_geographie        # 8 régions, 34 préfectures, communes urbaines
python manage.py createsuperuser
python manage.py runserver
```

Application : http://localhost:8000 · Administration (référentiels, paramètres, utilisateurs) : http://localhost:8000/admin

Données fictives pour tester : `python manage.py donnees_demo --nombre 60` (ajoutez `--admin` pour
créer le compte `demo`, mot de passe défini par `DEMO_PASSWORD` dans `.env`).

Tests : `python manage.py test apps`

## Architecture

| App | Rôle | Cahier des charges |
|---|---|---|
| `apps/core` | Modèles abstraits (horodatage, suppression logique), tableau de bord | §6, §20 |
| `apps/comptes` | Utilisateur personnalisé, 6 rôles, droits métier, périmètre géographique | §5 |
| `apps/geographie` | Région → Préfecture → Commune → Quartier | §4 |
| `apps/parametres` | Paramètres système (seuils de validité passeport, blocage…) | §9 |
| `apps/pelerins` | Campagne Hadj, Agence, Groupe, Pèlerin, Passeport, Dossier Hadj, Documents, Doublons, recherche, exports | §7–13, §16, §18, §22 |
| `apps/badges` | Badge, QR Code sécurisé, vérification | §14, §15 |
| `apps/journal` | Historique automatique (ancienne/nouvelle valeur), journal des connexions | §19 |

### Choix structurants

- **Identifiants** : clé technique interne (`id`) + numéro de passeport comme identifiant métier
  unique (contrainte en base, hors enregistrements supprimés). Chaque pèlerin a un matricule
  `PEL-0000001` ; chaque dossier annuel un numéro `H2027-000001` (§31).
- **Multi-années** : un pèlerin → plusieurs `DossierHadj` (un par campagne) (§22).
- **Validité du passeport** (`pelerins/services.py`) : classement Conforme / Attention / Non conforme / Expiré,
  calculé par rapport à une date de référence (date du jour, départ ou retour de la campagne) + seuil
  en mois configurable dans les paramètres. Le même calcul existe en filtre SQL pour les listes et stats.
- **Contrôle à la saisie** : vérification AJAX du numéro de passeport (doublon, expiration) ; un doublon
  empêche l'enregistrement, un passeport expiré bloque le dossier si le paramètre l'exige.
- **Droits** : `comptes/roles.py` associe chaque rôle à des permissions métier ; `Utilisateur.filtrer_perimetre()`
  restreint toutes les requêtes à la région / préfecture / commune de l'utilisateur.
- **QR Code** : ne contient qu'un jeton aléatoire (aucune donnée personnelle) ; la vérification exige
  un compte autorisé et est journalisée. Rééditer un badge révoque l'ancien.
- **Suppression logique** partout (`est_supprime`), avec motif obligatoire.
- **Traçabilité** : les modèles sensibles sont journalisés automatiquement par signaux (`journal/apps.py`).

## Production

- `DEBUG=False`, `SECRET_KEY` robuste, `ALLOWED_HOSTS`, `DATABASE_URL=postgres://…` (PostgreSQL recommandé).
- HTTPS derrière un proxy (Nginx) : les en-têtes HSTS / cookies sécurisés s'activent automatiquement.
- `python manage.py collectstatic` ; servir `media/` via le proxy **avec contrôle d'accès** (documents sensibles).
- Sauvegardes : `pg_dump` planifié + copie du dossier `media/`, avec plusieurs générations (§26).

## Reste à faire (prochaines itérations)

- Écrans dédiés : gestion des utilisateurs et paramètres hors admin Django, page Statistiques détaillée
  (par préfecture / commune / quartier, par semaine / mois).
- Fusion de doublons, ajout d'un nouveau passeport à un pèlerin existant, nouveau dossier pour une autre année.
- Impression des badges en masse (PDF planche), export des badges.
- Service protégé des fichiers médias, chiffrement des champs sensibles si requis.
- Mode hors ligne / synchronisation (§27), application Android, OCR des passeports (§30).
