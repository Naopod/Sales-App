"""
Service pour le sous-onglet ANALYSE GÉOGRAPHIQUE
Analyse géographique approfondie : pays, zones, scoring
AUTONOME - Ne dépend d'aucun autre fichier de services
"""
import pandas as pd
import numpy as np


def analyze_geographic_data(df_final: pd.DataFrame, granularity: str = 'month') -> dict:
    """
    Analyse géographique approfondie : pays, zones, scoring
    
    Args:
        df_final: DataFrame nettoyé issu de process_raw_data
        granularity: 'month', 'quarter', 'year' - granularité d'agrégation temporelle
    
    Returns:
        dict contenant les statistiques géographiques
    """
    
    # AFFICHAGE DATAFRAME FILTRÉ
    print("\n" + "="*80)
    print(f"ANALYSE GÉOGRAPHIQUE - DataFrame filtré (granularité: {granularity})")
    print("="*80)
    print(f"Shape: {df_final.shape[0]:,} lignes × {df_final.shape[1]} colonnes\n")
    print(df_final.head(10))
    print("="*80 + "\n")
    
    # Mapping des colonnes temporelles selon la granularité
    time_columns = {
        'month': 'Month',
        'quarter': 'Quarter',
        'year': 'Fiscal_Year_Label'
    }
    time_col = time_columns.get(granularity, 'Month')
    
    # Note: Pour l'analyse géographique, on agrège toujours sur toute la période
    # La granularité est surtout informative pour le contexte d'utilisation
    
    # 1. PERFORMANCE PAR PAYS
    
    stats_pays = df_final.groupby('Country').agg({
        'Montant': ['sum', 'mean', 'median', 'std', 'count'],
        'Quantité': ['sum', 'mean'],
        'PU Net': ['mean', 'median'],
        'Cpt Client': 'nunique',
        'N° Bon': 'nunique',
        'Famille': 'nunique'
    }).round(2)
    
    stats_pays.columns = ['CA_Total', 'CA_Moyen', 'CA_Median', 'CA_StdDev', 'Nb_Ventes',
                           'Qty_Total', 'Qty_Moyenne', 'PU_Moyen', 'PU_Median',
                           'Nb_Clients', 'Nb_Commandes', 'Nb_Familles']
    
    # Calculs complémentaires
    stats_pays['Part_Pct'] = (stats_pays['CA_Total'] / stats_pays['CA_Total'].sum() * 100).round(1)
    stats_pays = stats_pays.sort_values('CA_Total', ascending=False)
    stats_pays['Rang'] = range(1, len(stats_pays) + 1)
    stats_pays['CA_par_Client'] = (stats_pays['CA_Total'] / stats_pays['Nb_Clients']).round(2)
    stats_pays['Panier_Moyen'] = (stats_pays['CA_Total'] / stats_pays['Nb_Commandes']).round(2)
    stats_pays['Tx_Penetration_Pct'] = (stats_pays['Nb_Clients'] / stats_pays['Nb_Clients'].sum() * 100).round(1)
    
    # 2. ZONES GÉOGRAPHIQUES
    
    zones_geo = {
        'Europe Ouest': ['FR', 'BE', 'DE', 'NL', 'LU'],
        'Europe Nord': ['GB', 'DK', 'SE', 'NO', 'IE'],
        'Europe Sud': ['ES', 'IT', 'PT', 'GR'],
        'Europe Est': ['PL', 'CZ', 'AT', 'CH', 'HU', 'SK', 'RO', 'HR', 'BG', 'RS', 'MK', 'LT'],
        'Autres': []
    }
    
    def get_zone(pays):
        for zone, pays_list in zones_geo.items():
            if pays in pays_list:
                return zone
        return 'Autres'
    
    # Ajouter la colonne Zone à stats_pays
    stats_pays['Zone'] = stats_pays.index.map(get_zone)
    
    df_geo = df_final.copy()
    df_geo['Zone'] = df_geo['Country'].apply(get_zone)
    
    stats_zone = df_geo.groupby('Zone').agg({
        'Montant': ['sum', 'mean'],
        'Cpt Client': 'nunique',
        'N° Bon': 'nunique',
        'Country': 'nunique'
    }).round(2)
    
    stats_zone.columns = ['CA_Total', 'CA_Moyen', 'Nb_Clients', 'Nb_Commandes', 'Nb_Pays']
    stats_zone['Part_Pct'] = (stats_zone['CA_Total'] / stats_zone['CA_Total'].sum() * 100).round(1)
    stats_zone = stats_zone.sort_values('CA_Total', ascending=False)
    
    # ─────────────────────────────────────────────────────────────────────
    # 3. SCORING PAYS
    # ─────────────────────────────────────────────────────────────────────
    
    # 3. SCORING DE PERFORMANCE PAR PAYS
    
    # Normalisation des indicateurs (0-100)
    stats_pays['Score_CA'] = (stats_pays['CA_Total'] / stats_pays['CA_Total'].max() * 100).round(1)
    stats_pays['Score_Panier'] = (stats_pays['Panier_Moyen'] / stats_pays['Panier_Moyen'].max() * 100).round(1)
    stats_pays['Score_Clients'] = (stats_pays['Nb_Clients'] / stats_pays['Nb_Clients'].max() * 100).round(1)
    
    # Score global (moyenne pondérée)
    stats_pays['Score_Global'] = (
        stats_pays['Score_CA'] * 0.5 + 
        stats_pays['Score_Panier'] * 0.3 + 
        stats_pays['Score_Clients'] * 0.2
    ).round(1)
    
    stats_pays = stats_pays.sort_values('Score_Global', ascending=False)

    top10_score = stats_pays.head(10)
    
    # Classification des pays
    def classify_pays(score):
        if score >= 70:
            return 'Excellence'
        elif score >= 50:
            return 'Performant'
        elif score >= 30:
            return 'Moyen'
        else:
            return 'À Développer'
    
    stats_pays['Classification'] = stats_pays['Score_Global'].apply(classify_pays)
    
    classif_summary = stats_pays.groupby('Classification').agg({
        'CA_Total': ['sum', 'count']
    })
    classif_summary.columns = ['CA_Total', 'Nb_Pays']
    classif_summary = classif_summary.reindex(['Excellence', 'Performant', 'Moyen', 'À Développer'])
    classif_summary = classif_summary.fillna(0)
    classif_summary['Part_CA_Pct'] = (classif_summary['CA_Total'] / classif_summary['CA_Total'].sum() * 100).round(1)
    
    score_moyens = stats_pays.groupby('Classification')['Score_Global'].mean().round(1)
    classif_summary['Score_Moyen'] = classif_summary.index.map(score_moyens).fillna(0)
    
    # 4. GÉNÉRATION DES VISUALISATIONS
    
    # Génération des graphiques Plotly
    geo_graphs = {}
    
    from .visualizations import viz_geographic
    
    # Graphique CA par pays
    ca_chart = viz_geographic.create_geographic_ca_chart(stats_pays)
    if ca_chart:
        geo_graphs['ca_by_country'] = ca_chart
    
    # Graphique performance par zone
    zone_chart = viz_geographic.create_zone_performance_chart(stats_zone)
    if zone_chart:
        geo_graphs['zone_performance'] = zone_chart
    
    # Graphique de classification
    classif_chart = viz_geographic.create_classification_chart(stats_pays)
    if classif_chart:
        geo_graphs['classification'] = classif_chart
    
    # Distribution des scores
    score_chart = viz_geographic.create_score_distribution_chart(stats_pays)
    if score_chart:
        geo_graphs['score_distribution'] = score_chart
    
    return {
        'stats_pays': stats_pays,
        'stats_zone': stats_zone,
        'classif_summary': classif_summary,
        'top10_score': top10_score,
        'geo_graphs': geo_graphs
    }


def generate_geographic_analysis(df_final: pd.DataFrame) -> dict:
    """
    Wrapper pour l'analyse géographique - utilisé dans les views
    
    Args:
        df_final: DataFrame nettoyé
    
    Returns:
        dict avec l'analyse complète géographique
    """
    return analyze_geographic_data(df_final)
