# Client Analytics Portal

Application web Django pour l'analyse de données clients avec upload Excel, statistiques, modélisation et clustering.

## Installation

1. **Créer un environnement virtuel**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# ou
source venv/bin/activate  # Linux/Mac
```

2. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

3. **Appliquer les migrations**
```bash
python manage.py migrate
```

4. **Créer un superutilisateur (optionnel)**
```bash
python manage.py createsuperuser
```

5. **Lancer le serveur**
```bash
python manage.py runserver
```

6. **Accéder à l'application**
Ouvrir http://127.0.0.1:8000/ dans votre navigateur

## Utilisation

### Workflow
1. **Home** : Uploader un fichier Excel ou sélectionner un dataset démo
2. **Overview** : Visualiser les informations générales du dataset
3. **Stats** : Analyser les statistiques et distributions
4. **Modeling** : Entraîner des modèles de classification ou régression
5. **Clustering** : Effectuer du clustering K-Means et exporter les résultats

### Format de données recommandé
Votre fichier Excel doit contenir :
- Des colonnes numériques (âge, montant, quantité, etc.)
- Des colonnes catégorielles (pays, catégorie, segment, etc.)
- Au moins 50 lignes pour des analyses significatives

Exemples de colonnes :
- `customer_id`, `age`, `country`, `total_spent`, `num_orders`, `category`, `churn`

## Fonctionnalités

### Overview
- Dimensions du dataset
- Types de données
- Valeurs manquantes
- Statistiques descriptives

### Stats
- Histogrammes pour variables numériques
- Graphiques en barres pour variables catégorielles
- Heatmap de corrélation
- Sélection de variables spécifiques

### Modeling
- Classification (Logistic Regression, Random Forest Classifier)
- Régression (Linear Regression, Random Forest Regressor)
- Métriques : Accuracy, F1-Score, RMSE, R²
- Matrice de confusion
- Importance des features

### Clustering
- Algorithme K-Means
- Choix du nombre de clusters (2-10)
- Visualisation PCA 2D
- Métriques : Inertia, Silhouette Score
- Export CSV avec labels de clusters

## Structure du Projet

```
analytics_portal/
├── manage.py
├── requirements.txt
├── README.md
├── analytics_portal/          # Configuration Django
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
└── client_analytics/          # Application principale
    ├── models.py              # Modèle Dataset
    ├── forms.py               # Formulaires
    ├── views.py               # Vues
    ├── urls.py                # Routes
    ├── admin.py               # Interface admin
    ├── services/              # Logique métier
    │   ├── dataset_io.py      # Chargement de données
    │   ├── profiling.py       # Profilage
    │   ├── stats.py           # Statistiques
    │   ├── modeling.py        # Machine Learning
    │   └── clustering.py      # Clustering
    ├── templates/             # Templates HTML
    ├── static/                # CSS/JS
    ├── demo_data/             # Datasets démo
    └── migrations/            # Migrations DB
```

## Tests

```bash
python manage.py test client_analytics
```

## Technologies

- **Backend** : Django 5.0, Python 3.11+
- **Data Processing** : pandas, scikit-learn
- **Visualization** : plotly
- **Frontend** : Bootstrap 5
- **Database** : SQLite (par défaut)

## Limites

- Taille maximale de fichier : 10MB
- Formats supportés : .xlsx, .xls
- Base de données : SQLite (production nécessite PostgreSQL/MySQL)

## Support

Pour toute question ou problème, consultez la documentation Django : https://docs.djangoproject.com/
