# Analyse Client Type PowerBI - Documentation des Modifications

## Vue d'ensemble
Ce document décrit les modifications apportées au projet `client_analytics` pour ajouter une analyse client type PowerBI dans la section "Analyse client / Client 360".

## Modifications effectuées

### 1. data_processing.py
**Fichier**: `client_analytics/services/data_processing.py`

**Modification**: Ajout de "Libelle 2" dans les colonnes finales
- Ligne ajoutée dans `colonnes_finales`: `"Libelle 2"`
- **Raison**: Permet à la colonne Libelle 2 de survivre au preprocessing pour être utilisée dans les tables produits

### 2. views.py
**Fichier**: `client_analytics/views.py`

**Modifications**:
1. Lecture du paramètre GET `client_families` (multi-select)
   ```python
   selected_client_families = request.GET.getlist('client_families')
   ```

2. Calcul des options de familles disponibles pour le client sélectionné
   ```python
   family_options = []
   if selected_client:
       # Extraction des familles uniques pour ce client
       families = sorted(df_client_temp[family_col].dropna().unique().tolist())
       family_options = [{'value': f, 'label': f} for f in families]
   ```

3. Passage du paramètre `selected_families` à `analyze_client_portfolio_full()`

4. Ajout des variables au contexte du template:
   - `selected_client_families`
   - `family_options`

### 3. analysis_clients.py
**Fichier**: `client_analytics/services/analysis_clients.py`

**Modifications principales**:

1. **Signature de la fonction** `analyze_client_portfolio_full()`
   ```python
   def analyze_client_portfolio_full(
       df: pd.DataFrame,
       client_id: str,
       time_granularity: str = 'month',
       top_n_families: int = 8,
       top_n_products: int = 10,
       selected_families: list = None,  # NOUVEAU
   ) -> dict:
   ```

2. **Filtrage par familles** (après création de df_client)
   ```python
   if selected_families and family_col and family_col in df_client.columns:
       df_client = df_client[df_client[family_col].isin(selected_families)].copy()
       if df_client.empty:
           portfolio['error'] = 'Aucune donnée pour les familles sélectionnées'
           return portfolio
   ```

3. **Fonction helper** `format_table_html(df_pivot, title)` pour formater les DataFrames en HTML Bootstrap

4. **Nouvelles tables** ajoutées à `portfolio['tables']`:
   - `products_fy_amount_table_html`: Produits × Années fiscales (Montant)
   - `products_fy_qty_table_html`: Produits × Années fiscales (Quantité)
   - `efq_family_amount_table_html`: EF&Q × Famille (Montant)
   - `efq_family_qty_table_html`: EF&Q × Famille (Quantité)

5. **Nouveaux graphiques** ajoutés à `portfolio['graphs']`:
   - `chart_efq_family_amount_html`: Graphique empilé Montant par EF&Q et Famille
   - `chart_efq_family_qty_html`: Graphique empilé Quantité par EF&Q et Famille

**Logique des tables**:

- **Produits × FY**: 
  - Index: Produit (Libelle 1 ou "Libelle 1 — Libelle 2" si disponible)
  - Colonnes: Années fiscales (Fiscal_Year, FY, Exercice, EF, Year_FY, ou Year en fallback)
  - Valeurs: Somme de Montant ou Quantité
  - Tri: Par Total décroissant
  - Ligne/Colonne Total ajoutée

- **EF&Q × Famille**:
  - Colonne période EF_Q créée: FY + "-Q" + Quarter_Num
  - Index: EF_Q (ex: "2024-Q1")
  - Colonnes: Familles
  - Valeurs: Somme de Montant ou Quantité
  - Colonne Total ajoutée

### 4. viz_clients.py
**Fichier**: `client_analytics/services/visualizations/viz_clients.py`

**Nouvelle fonction** ajoutée:
```python
def create_client_period_family_stacked(
    records: list, 
    value_key: str = 'value', 
    title: str = 'Analyse par période et famille'
) -> str:
```

**Fonctionnalité**: Crée un graphique en barres empilées (stacked bar) avec Plotly
- **Input**: Liste de dicts avec clés `period`, `family`, et `value`
- **Output**: HTML du graphique Plotly
- **Configuration**: 
  - barmode='stack'
  - template='plotly_white'
  - height=520
  - rotation ticks x à -45°
  - légende verticale à droite

### 5. stats.html
**Fichier**: `client_analytics/templates/client_analytics/stats.html`

**Modifications**:
1. Formulaire Client 360 restructuré:
   - Colonne client: `col-lg-6` (au lieu de `col-lg-8`)
   - Nouvelle colonne famille: `col-lg-4` avec select multiple
   - Colonne bouton: `col-lg-2` (au lieu de `col-lg-4`)

2. Ajout du sélecteur de familles (multi-select):
   ```html
   <select class="form-select" name="client_families" id="family-select" multiple size="4">
       {% for opt in family_options %}
           <option value="{{ opt.value }}" {% if opt.value in selected_client_families %}selected{% endif %}>
               {{ opt.label }}
           </option>
       {% endfor %}
   </select>
   ```

3. JavaScript pour activer/désactiver le sélecteur selon le client choisi

### 6. _client360_block.html
**Fichier**: `client_analytics/templates/client_analytics/partials/_client360_block.html`

**Nouvelle section** ajoutée (avant les `{% endif %}` finaux):

Structure avec onglets Bootstrap:
1. **Produits × FY**:
   - Sous-section Montant
   - Sous-section Quantité

2. **EF&Q × Famille**:
   - Sous-section Montant
   - Sous-section Quantité

3. **Graphiques Empilés**:
   - Graphique Montant
   - Graphique Quantité

Chaque section affiche:
- Le contenu HTML/graph si disponible
- Un message "Aucune donnée disponible" sinon

### 7. Tests
**Fichier**: `client_analytics/tests/test_client_powerbi.py` (nouveau)

**Tests créés**:

**TestClientPowerBIAnalysis**:
- `test_analyze_client_with_selected_families`: Filtrage par famille
- `test_products_fy_table_generation`: Génération table Produits × FY
- `test_efq_family_tables_generation`: Génération matrices EF&Q × Famille
- `test_efq_family_charts_generation`: Génération graphiques empilés
- `test_empty_families_filter`: Filtre vide (toutes les familles)
- `test_nonexistent_family_filter`: Familles inexistantes
- `test_libelle2_handling`: Gestion de Libelle 2 manquant
- `test_missing_fy_fallback_to_year`: Fallback FY → Year

**TestVisualizationFunctions**:
- `test_create_client_period_family_stacked`: Création graphiques empilés
- `test_stacked_chart_empty_records`: Records vides
- `test_stacked_chart_missing_keys`: Clés manquantes

## Gestion des cas limites

### Colonnes manquantes
- **Fiscal_Year**: Fallback vers Year
- **Quarter/Trimestre_Num**: Fallback vers None (pas de table EF&Q générée)
- **Libelle 2**: Utilisation uniquement de Libelle 1
- **Montant/Quantité**: Tables non générées si colonnes absentes

### DataFrames vides
- Filtrage de familles inexistantes → erreur "Aucune donnée pour les familles sélectionnées"
- Client sans données → erreur "Client introuvable ou sans lignes"
- Tables vides → message "Aucune donnée disponible"

### Format des données
- Conversion automatique en numérique des colonnes Montant/Quantité
- Gestion des valeurs NaN/null
- Tri par Total pour une meilleure lisibilité

## Architecture respectée

✅ **Services**: `analysis_clients.py` pour la logique métier  
✅ **Visualizations**: `viz_clients.py` pour les graphiques  
✅ **Templates**: Partials pour la réutilisabilité  
✅ **Logging**: Utilisation de `print()` pour debug (compatible avec logger)  
✅ **Robustesse**: Gestion d'erreurs avec try/except  
✅ **Compatibilité**: Ne casse aucune feature existante  

## Utilisation

### Côté utilisateur
1. Aller sur la page Stats → Onglet "Clients"
2. Choisir un client dans le sélecteur
3. (Optionnel) Sélectionner une ou plusieurs familles pour filtrer
4. Cliquer sur "Afficher"
5. Explorer la nouvelle section "Analyse Client PowerBI-like" avec 3 onglets

### Paramètres GET conservés
- `?tab=clients` : Onglet actif
- `?granularity=month|quarter|year` : Granularité temporelle
- `?client=XXX` : Client sélectionné
- `?client_families=FAM1&client_families=FAM2` : Familles filtrées (multi-values)

## Tests manuels suggérés

1. ✅ Sélectionner un client → Vérifier que les familles se chargent
2. ✅ Filtrer par 1 famille → Vérifier que les données sont filtrées
3. ✅ Filtrer par plusieurs familles → Vérifier l'agrégation
4. ✅ Changer de granularité (month/quarter/year) → Vérifier les libellés
5. ✅ Vérifier les tables HTML (Produits × FY, EF&Q × Famille)
6. ✅ Vérifier les graphiques empilés (interactivité Plotly)
7. ✅ Tester avec un dataset sans Libelle 2 → Pas de crash
8. ✅ Tester avec un dataset sans Fiscal_Year → Fallback Year

## Commandes pour exécuter les tests

```bash
# Tous les tests
python manage.py test client_analytics.tests.test_client_powerbi

# Un test spécifique
python manage.py test client_analytics.tests.test_client_powerbi.TestClientPowerBIAnalysis.test_products_fy_table_generation

# Avec verbose
python manage.py test client_analytics.tests.test_client_powerbi -v 2
```

## Notes techniques

- **Bootstrap 5** utilisé pour les onglets (nav-tabs)
- **Plotly CDN** pour les graphiques interactifs
- **Pandas pivot_table** pour les matrices croisées
- **Django template |safe** pour afficher HTML brut
- **GET multi-value** via `.getlist()` pour le multi-select

## Améliorations futures possibles

1. Export Excel des tables Produits × FY et EF&Q × Famille
2. Filtres supplémentaires (pays, période, etc.)
3. Graphiques supplémentaires (heatmap, etc.)
4. Cache des résultats pour améliorer les performances
5. Téléchargement des graphiques en PNG/SVG
6. Pagination pour les grandes tables
7. AJAX pour éviter le rechargement de page complet

## Conclusion

Toutes les fonctionnalités demandées ont été implémentées avec succès:
- ✅ Slicer Famille (multi-select)
- ✅ Tables Produits × FY (Montant + Quantité)
- ✅ Matrices EF&Q × Famille (Montant + Quantité) 
- ✅ Graphiques empilés (Montant + Quantité)
- ✅ Gestion robuste des colonnes manquantes
- ✅ Tests unitaires complets
- ✅ Aucune feature cassée

Le code respecte l'architecture existante et suit les bonnes pratiques Django/Pandas/Plotly.
