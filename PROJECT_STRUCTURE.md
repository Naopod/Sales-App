# Arborescence Complète du Projet

```
analytics_portal/
│
├── manage.py                          # Script de gestion Django
├── requirements.txt                   # Dépendances Python
├── README.md                          # Documentation complète
├── .gitignore                         # Fichiers à ignorer par Git
├── db.sqlite3                         # Base de données (créée après migration)
│
├── analytics_portal/                  # Configuration du projet Django
│   ├── __init__.py
│   ├── settings.py                    # Paramètres Django
│   ├── urls.py                        # URLs principales
│   ├── wsgi.py                        # Configuration WSGI
│   └── asgi.py                        # Configuration ASGI
│
├── client_analytics/                  # Application principale
│   ├── __init__.py
│   ├── admin.py                       # Interface d'administration
│   ├── apps.py                        # Configuration de l'app
│   ├── forms.py                       # Formulaires Django
│   ├── models.py                      # Modèle Dataset
│   ├── urls.py                        # URLs de l'application
│   ├── views.py                       # Vues (contrôleurs)
│   ├── tests.py                       # Tests unitaires
│   │
│   ├── services/                      # Logique métier
│   │   ├── __init__.py
│   │   ├── dataset_io.py              # Chargement de données
│   │   ├── profiling.py               # Profilage de dataset
│   │   ├── stats.py                   # Statistiques et visualisations
│   │   ├── modeling.py                # Machine Learning
│   │   └── clustering.py              # Clustering K-Means
│   │
│   ├── migrations/                    # Migrations de base de données
│   │   ├── __init__.py
│   │   └── 0001_initial.py            # Migration initiale
│   │
│   ├── management/                    # Commandes personnalisées
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       └── generate_demo_data.py  # Génération de datasets démo
│   │
│   ├── templatetags/                  # Filtres de template personnalisés
│   │   ├── __init__.py
│   │   └── custom_filters.py          # Filtres (get_item, intcomma)
│   │
│   ├── demo_data/                     # Datasets de démonstration
│   │   ├── demo_clients_1.xlsx        # (généré par commande)
│   │   └── demo_clients_2.xlsx        # (généré par commande)
│   │
│   ├── templates/                     # Templates HTML
│   │   └── client_analytics/
│   │       ├── base.html              # Template de base
│   │       ├── home.html              # Page d'accueil
│   │       ├── workflow.html          # Explication du workflow
│   │       ├── dataset_overview.html  # Vue d'ensemble du dataset
│   │       ├── stats.html             # Statistiques
│   │       ├── modeling.html          # Modélisation ML
│   │       └── clustering.html        # Clustering K-Means
│   │
│   └── static/                        # Fichiers statiques
│       └── client_analytics/
│           └── app.css                # Styles CSS personnalisés
│
└── media/                             # Fichiers uploadés (créé automatiquement)
    └── datasets/                      # Datasets uploadés
```

## Fichiers Créés

### Racine du Projet
- ✅ manage.py
- ✅ requirements.txt
- ✅ README.md
- ✅ .gitignore

### analytics_portal/ (Configuration)
- ✅ __init__.py
- ✅ settings.py
- ✅ urls.py
- ✅ wsgi.py
- ✅ asgi.py

### client_analytics/ (Application)
- ✅ __init__.py
- ✅ admin.py
- ✅ apps.py
- ✅ forms.py
- ✅ models.py
- ✅ urls.py
- ✅ views.py
- ✅ tests.py

### client_analytics/services/
- ✅ __init__.py
- ✅ dataset_io.py
- ✅ profiling.py
- ✅ stats.py
- ✅ modeling.py
- ✅ clustering.py

### client_analytics/migrations/
- ✅ __init__.py
- ✅ 0001_initial.py

### client_analytics/management/commands/
- ✅ __init__.py (management/)
- ✅ __init__.py (commands/)
- ✅ generate_demo_data.py

### client_analytics/templatetags/
- ✅ __init__.py
- ✅ custom_filters.py

### client_analytics/templates/client_analytics/
- ✅ base.html
- ✅ home.html
- ✅ workflow.html
- ✅ dataset_overview.html
- ✅ stats.html
- ✅ modeling.html
- ✅ clustering.html

### client_analytics/static/client_analytics/
- ✅ app.css

## Installation et Lancement

```bash
# 1. Créer un environnement virtuel
python -m venv venv
venv\Scripts\activate  # Windows

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Appliquer les migrations
python manage.py migrate

# 4. Générer les datasets démo
python manage.py generate_demo_data

# 5. Créer un superutilisateur (optionnel)
python manage.py createsuperuser

# 6. Lancer le serveur
python manage.py runserver

# 7. Accéder à l'application
# http://127.0.0.1:8000/
```

## Tests

```bash
python manage.py test client_analytics
```

## Fonctionnalités Implémentées

✅ Upload de fichiers Excel
✅ Sélection de datasets démo
✅ Overview du dataset avec statistiques descriptives
✅ Visualisations statistiques interactives (Plotly)
✅ Modélisation ML (Classification et Régression)
✅ Clustering K-Means avec visualisation PCA
✅ Export CSV des résultats de clustering
✅ Interface responsive (Bootstrap 5)
✅ Tests unitaires
✅ Interface d'administration Django

## Technologies Utilisées

- Django 5.0
- pandas 2.0+
- scikit-learn 1.3+
- plotly 5.17+
- openpyxl 3.1+
- Bootstrap 5 (CDN)
- SQLite

**Projet prêt à lancer ! Aucun fichier manquant.**
