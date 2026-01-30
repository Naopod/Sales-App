"""
Service pour le sous-onglet ANALYSE SÉRIE TEMPORELLE
Analyse temporelle avancée avec saisonnalité, tendances, STL, ARIMA
AUTONOME - Ne dépend d'aucun autre fichier de services
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from statsmodels.tsa.stattools import adfuller, kpss
import warnings
warnings.filterwarnings('ignore')

# Import visualizations
from .visualizations.viz_time_series import create_stl_decomposition_plot


def analyze_temporal_data(df_final: pd.DataFrame) -> dict:
    """
    Analyse temporelle approfondie : Mois, Trimestre, Année Fiscale (Avril->Mars)

    Args:
        df_final: DataFrame nettoyé issu de process_raw_data

    Returns:
        dict contenant les statistiques par trimestre, mois et année fiscale
    """
    
    print("=" * 100)
    print("                    📅 ANALYSE TEMPORELLE APPROFONDIE")
    print("=" * 100)

    # Préparation des données temporelles
    df_temp = df_final.copy()
    
    # Extraction du numéro de trimestre depuis "2025Q1" -> 1
    if 'Quarter' in df_temp.columns:
        df_temp['Trimestre_Num'] = df_temp['Quarter'].astype(str).str.extract(r'Q(\d+)')[0].astype(int)
    
    # Extraction du nom du mois depuis "2025-01"
    if 'Month' in df_temp.columns:
        df_temp['Mois_Datetime'] = pd.to_datetime(df_temp['Month'] + '-01')
        df_temp['Mois_Nom'] = df_temp['Mois_Datetime'].dt.strftime('%B')
        df_temp['Mois_Num'] = df_temp['Mois_Datetime'].dt.month

    # ─────────────────────────────────────────────────────────────────────
    # 1. ANALYSE PAR TRIMESTRE FISCAL
    # ─────────────────────────────────────────────────────────────────────

    print("\n" + "─" * 100)
    print("📊 1. PERFORMANCE PAR TRIMESTRE FISCAL (Avril→Mars)")
    print("─" * 100)

    if 'Trimestre_Num' in df_temp.columns and 'Fiscal_Year_Label' in df_temp.columns:
        stats_trim = df_temp.groupby(['Fiscal_Year_Label', 'Trimestre_Num']).agg({
            'Montant': ['sum', 'mean', 'median', 'std', 'count'],
            'Quantité': ['sum', 'mean'],
            'PU Net': ['mean', 'median'],
            'Cpt Client': 'nunique',
            'N° Bon': 'nunique'
        }).round(2)

        stats_trim.columns = ['CA_Total', 'CA_Moyen', 'CA_Median', 'CA_StdDev', 'Nb_Ventes', 
                              'Qty_Total', 'Qty_Moyenne', 'PU_Moyen', 'PU_Median', 
                              'Nb_Clients', 'Nb_Commandes']

        # Calculs complémentaires
        stats_trim['Part_%'] = (stats_trim.groupby(level=0)['CA_Total']
                                .transform(lambda x: (x / x.sum() * 100))).round(1)
        stats_trim['CV_%'] = (stats_trim['CA_StdDev'] / stats_trim['CA_Moyen'] * 100).round(1)
        stats_trim['CA_par_Client'] = (stats_trim['CA_Total'] / stats_trim['Nb_Clients']).round(2)

        print("\n" + stats_trim.to_string())

        # Analyse de tendance pour la dernière année fiscale
        dernier_fy = df_temp['Fiscal_Year_Label'].max()
        stats_trim_fy = stats_trim.loc[dernier_fy]
        
        if len(stats_trim_fy) >= 2:
            print(f"\n📈 TENDANCES CLÉS ({dernier_fy}) :")
            croissance = ((stats_trim_fy.iloc[-1]['CA_Total'] / stats_trim_fy.iloc[0]['CA_Total']) - 1) * 100
            print(f"   • Croissance Q1→Q{len(stats_trim_fy)}: {croissance:+.1f}%")
            meilleur_q = stats_trim_fy['CA_Total'].idxmax()
            pire_q = stats_trim_fy['CA_Total'].idxmin()
            print(f"   • Meilleur trimestre   : Q{meilleur_q} ({stats_trim_fy.loc[meilleur_q, 'CA_Total']:,.0f}€, {stats_trim_fy.loc[meilleur_q, 'Part_%']:.1f}%)")
            print(f"   • Pire trimestre       : Q{pire_q} ({stats_trim_fy.loc[pire_q, 'CA_Total']:,.0f}€, {stats_trim_fy.loc[pire_q, 'Part_%']:.1f}%)")
            print(f"   • Trimestre + stable   : Q{stats_trim_fy['CV_%'].idxmin()} (CV={stats_trim_fy['CV_%'].min():.1f}%)")
            print(f"   • Trimestre + volatile : Q{stats_trim_fy['CV_%'].idxmax()} (CV={stats_trim_fy['CV_%'].max():.1f}%)")
    else:
        stats_trim = None
        print("⚠️ Colonnes Quarter ou Fiscal_Year_Label manquantes")

    # ─────────────────────────────────────────────────────────────────────
    # 2. ANALYSE PAR MOIS
    # ─────────────────────────────────────────────────────────────────────

    print("\n" + "─" * 100)
    print("📊 2. PERFORMANCE PAR MOIS")
    print("─" * 100)

    if 'Month' in df_temp.columns and 'Fiscal_Year_Label' in df_temp.columns:
        stats_mois = df_temp.groupby(['Fiscal_Year_Label', 'Month']).agg({
            'Montant': ['sum', 'mean', 'count'],
            'Quantité': 'sum',
            'Cpt Client': 'nunique',
            'N° Bon': 'nunique'
        }).round(2)

        stats_mois.columns = ['CA_Total', 'CA_Moyen', 'Nb_Ventes', 'Qty_Total', 'Nb_Clients', 'Nb_Commandes']
        stats_mois['Part_%'] = (stats_mois.groupby(level=0)['CA_Total']
                                .transform(lambda x: (x / x.sum() * 100))).round(1)

        # Ajouter les noms de mois
        mois_dict = {
            '01': 'Janvier', '02': 'Février', '03': 'Mars', '04': 'Avril',
            '05': 'Mai', '06': 'Juin', '07': 'Juillet', '08': 'Août',
            '09': 'Septembre', '10': 'Octobre', '11': 'Novembre', '12': 'Décembre'
        }
        stats_mois['Mois_Nom'] = stats_mois.index.get_level_values(1).str[-2:].map(mois_dict)

        print("\n" + stats_mois[['Mois_Nom', 'CA_Total', 'Nb_Ventes', 'CA_Moyen', 'Part_%']].to_string())

        # Top/Flop mois pour la dernière année fiscale
        stats_mois_fy = stats_mois.loc[dernier_fy] if dernier_fy in stats_mois.index else stats_mois

        print(f"\n🏆 TOP 3 MOIS ({dernier_fy}) :")
        top3_mois = stats_mois_fy.nlargest(3, 'CA_Total')
        for i, (idx, row) in enumerate(top3_mois.iterrows(), 1):
            print(f"   {i}. {row['Mois_Nom']:10s} : {row['CA_Total']:,.0f}€ ({row['Part_%']:.1f}%)")

        print(f"\n⚠️ BOTTOM 3 MOIS ({dernier_fy}) :")
        bottom3_mois = stats_mois_fy.nsmallest(3, 'CA_Total')
        for i, (idx, row) in enumerate(bottom3_mois.iterrows(), 1):
            print(f"   {i}. {row['Mois_Nom']:10s} : {row['CA_Total']:,.0f}€ ({row['Part_%']:.1f}%)")
    else:
        stats_mois = None
        print("⚠️ Colonnes Month ou Fiscal_Year_Label manquantes")

    # ─────────────────────────────────────────────────────────────────────
    # 3. ANALYSE PAR ANNÉE FISCALE
    # ─────────────────────────────────────────────────────────────────────

    print("\n" + "─" * 100)
    print("📊 3. PERFORMANCE PAR ANNÉE FISCALE (Avril→Mars)")
    print("─" * 100)

    if 'Fiscal_Year_Label' in df_temp.columns:
        stats_fy = df_temp.groupby('Fiscal_Year_Label').agg({
            'Montant': ['sum', 'mean', 'median', 'std', 'count'],
            'Quantité': ['sum', 'mean'],
            'PU Net': ['mean', 'median'],
            'Cpt Client': 'nunique',
            'N° Bon': 'nunique'
        }).round(2)

        stats_fy.columns = ['CA_Total', 'CA_Moyen', 'CA_Median', 'CA_StdDev', 'Nb_Ventes', 
                           'Qty_Total', 'Qty_Moyenne', 'PU_Moyen', 'PU_Median', 
                           'Nb_Clients', 'Nb_Commandes']

        stats_fy['Variation_%'] = stats_fy['CA_Total'].pct_change() * 100
        stats_fy['CA_par_Client'] = (stats_fy['CA_Total'] / stats_fy['Nb_Clients']).round(2)
        stats_fy['CA_par_Commande'] = (stats_fy['CA_Total'] / stats_fy['Nb_Commandes']).round(2)

        print("\n" + stats_fy.to_string())

        if len(stats_fy) >= 2:
            print("\n📈 CROISSANCE ANNUELLE :")
            for i in range(1, len(stats_fy)):
                fy_current = stats_fy.index[i]
                fy_previous = stats_fy.index[i-1]
                variation = stats_fy.loc[fy_current, 'Variation_%']
                print(f"   • {fy_previous} → {fy_current} : {variation:+.1f}%")
    else:
        stats_fy = None
        print("⚠️ Colonne Fiscal_Year_Label manquante")

    print("\n" + "=" * 100)

    return {
        'trimestre': stats_trim,
        'mois': stats_mois,
        'annee_fiscale': stats_fy
    }


def aggregate_by_time(df, granularity='month'):
    """Agrège les données selon une granularité temporelle"""
    if granularity not in ['month', 'quarter', 'year']:
        raise ValueError(f"Granularité '{granularity}' invalide")
    
    group_col = {'month': 'Month', 'quarter': 'Quarter', 'year': 'Year'}[granularity]
    
    if group_col not in df.columns:
        raise ValueError(f"Colonne '{group_col}' manquante")
    
    agg_dict = {}
    if 'Montant' in df.columns:
        agg_dict['Montant'] = 'sum'
    if 'Quantité' in df.columns:
        agg_dict['Quantité'] = 'sum'
    if 'Cpt Client' in df.columns:
        agg_dict['Cpt Client'] = 'nunique'
    if 'N° Bon' in df.columns:
        agg_dict['N° Bon'] = 'nunique'
    
    df_agg = df.groupby(group_col).agg(agg_dict)
    
    # Renommer colonnes
    df_agg.columns = ['_'.join(col).strip('_') if isinstance(col, tuple) else col 
                      for col in df_agg.columns]
    
    rename_map = {
        'Montant': 'CA_Total', 'Montant_sum': 'CA_Total',
        'Quantité': 'Qty_Total', 'Quantité_sum': 'Qty_Total',
        'Cpt Client': 'Nb_Clients', 'Cpt Client_nunique': 'Nb_Clients',
        'N° Bon': 'Nb_Commandes', 'N° Bon_nunique': 'Nb_Commandes'
    }
    
    df_agg.rename(columns=rename_map, inplace=True)
    
    if 'CA_Total' in df_agg.columns and 'Qty_Total' in df_agg.columns:
        df_agg['PU_Net_Moyen'] = df_agg['CA_Total'] / df_agg['Qty_Total']
    
    return df_agg


def get_temporal_metrics(df, granularity='month'):
    """Extrait des métriques temporelles"""
    df_agg = aggregate_by_time(df, granularity)
    
    return {
        'granularity': granularity,
        'periods': df_agg.index.tolist(),
        'ca_total': df_agg['CA_Total'].tolist() if 'CA_Total' in df_agg.columns else [],
        'qty_total': df_agg['Qty_Total'].tolist() if 'Qty_Total' in df_agg.columns else [],
        'nb_clients': df_agg['Nb_Clients'].tolist() if 'Nb_Clients' in df_agg.columns else [],
        'nb_commandes': df_agg['Nb_Commandes'].tolist() if 'Nb_Commandes' in df_agg.columns else []
    }


def generate_temporal_analysis(df):
    """
    Analyse temporelle complète avec STL, ARIMA, tests de stationnarité
    """
    results = {}
    graphs = {}
    
    # Agrégation mensuelle
    df_agg = aggregate_by_time(df, granularity='month')
    
    if 'CA_Total' in df_agg.columns and len(df_agg) > 12:
        # STL Decomposition - utilise la fonction de visualizations
        try:
            stl_plot = create_stl_decomposition_plot(df_agg)
            if stl_plot:
                graphs['stl_decomposition'] = stl_plot
        except Exception as e:
            results['stl_error'] = str(e)
    
        # Tests de stationnarité
        try:
            adf_result = adfuller(df_agg['CA_Total'])
            kpss_result = kpss(df_agg['CA_Total'])
            
            results['stationnarite'] = {
                'adf_statistic': float(adf_result[0]),
                'adf_pvalue': float(adf_result[1]),
                'adf_stationnaire': adf_result[1] < 0.05,
                'kpss_statistic': float(kpss_result[0]),
                'kpss_pvalue': float(kpss_result[1]),
                'kpss_stationnaire': kpss_result[1] > 0.05
            }
        except Exception as e:
            results['stationnarite_error'] = str(e)
    
    return {'results': results, 'graphs': graphs}


def generate_time_series_analysis(df, granularity='month'):
    """
    Génère l'analyse de séries temporelles complète
    
    Args:
        df: DataFrame avec colonnes temporelles
        granularity: 'month', 'quarter' ou 'year'
    
    Returns:
        dict: {
            'results': dict avec les résultats d'analyse,
            'graphs': dict avec les graphiques HTML,
            'metrics': dict avec les métriques temporelles
        }
    """
    print("📅 Génération de l'analyse de séries temporelles...")
    
    # Analyse complète
    analysis = generate_temporal_analysis(df)
    
    # Métriques avec granularité sélectable
    metrics = get_temporal_metrics(df, granularity=granularity)
    
    return {
        **analysis,
        'metrics': metrics,
        'granularity': granularity
    }


def aggregate_time_data(df, granularity='month'):
    """
    Agrège les données par période temporelle
    
    Args:
        df: DataFrame source
        granularity: 'month', 'quarter' ou 'year'
    
    Returns:
        DataFrame agrégé
    """
    return aggregate_by_time(df, granularity=granularity)
