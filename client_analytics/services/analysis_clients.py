"""
Service pour le sous-onglet ANALYSE CLIENTS
Analyse de la segmentation client, RFM, concentration
"""
import pandas as pd
import numpy as np


def analyze_clients(df_final: pd.DataFrame) -> dict:
    """
    Analyse détaillée des clients : segmentation, RFM, concentration
    
    Args:
        df_final: DataFrame nettoyé
    
    Returns:
        dict avec l'analyse des clients
    """
    
    print("="*100)
    print("                    👥 ANALYSE DES CLIENTS")
    print("="*100)
    
    results = {}
    
    # ─────────────────────────────────────────────────────────────────────
    # 1. STATISTIQUES DE BASE PAR CLIENT
    # ─────────────────────────────────────────────────────────────────────
    
    print("\n📊 1. STATISTIQUES PAR CLIENT")
    
    if 'Cpt Client' in df_final.columns and 'Montant' in df_final.columns:
        client_stats = df_final.groupby('Cpt Client').agg({
            'Montant': ['sum', 'count', 'mean'],
            'N° Bon': 'nunique' if 'N° Bon' in df_final.columns else 'count',
            'Date Fact.': ['min', 'max'] if 'Date Fact.' in df_final.columns else 'count'
        })
        
        client_stats.columns = ['CA_Total', 'Nb_Lignes', 'Panier_Moyen', 
                                'Nb_Commandes', 'Date_Premiere', 'Date_Derniere']
        
        # Calculs supplémentaires
        client_stats['CA_par_Commande'] = client_stats['CA_Total'] / client_stats['Nb_Commandes']
        
        # Calcul récence (jours depuis dernière commande)
        if 'Date_Derniere' in client_stats.columns:
            date_ref = df_final['Date Fact.'].max()
            client_stats['Recence_Jours'] = (date_ref - client_stats['Date_Derniere']).dt.days
        
        # Trier par CA
        client_stats = client_stats.sort_values('CA_Total', ascending=False)
        
        results['client_stats'] = client_stats
        
        print(f"   • Nombre total de clients : {len(client_stats):,}")
        print(f"   • CA total : {client_stats['CA_Total'].sum():,.0f}€")
        print(f"   • CA moyen par client : {client_stats['CA_Total'].mean():,.2f}€")
        print(f"   • CA médian par client : {client_stats['CA_Total'].median():,.2f}€")
    
    # ─────────────────────────────────────────────────────────────────────
    # 2. CONCENTRATION CLIENT (PARETO)
    # ─────────────────────────────────────────────────────────────────────
    
    print("\n📊 2. ANALYSE DE CONCENTRATION (PARETO)")
    
    if 'client_stats' in results:
        client_stats['Part_CA_Pct'] = (client_stats['CA_Total'] / client_stats['CA_Total'].sum() * 100)
        client_stats['Part_CA_Cumul'] = client_stats['Part_CA_Pct'].cumsum()
        
        # Top 20% clients
        top20_threshold = len(client_stats) * 0.2
        top20_clients = client_stats.head(int(top20_threshold))
        
        print(f"   • Top 20% clients ({int(top20_threshold)} clients) : {top20_clients['Part_CA_Pct'].sum():.1f}% du CA")
        
        # Top 10 clients
        top10 = client_stats.head(10)
        print(f"   • Top 10 clients : {top10['Part_CA_Pct'].sum():.1f}% du CA")
        
        results['top20_clients'] = top20_clients
        results['top10_clients'] = top10
        results['concentration_top20_pct'] = top20_clients['Part_CA_Pct'].sum()
        results['concentration_top10_pct'] = top10['Part_CA_Pct'].sum()
    
    # ─────────────────────────────────────────────────────────────────────
    # 3. SEGMENTATION RFM (Récence, Fréquence, Montant)
    # ─────────────────────────────────────────────────────────────────────
    
    print("\n📊 3. SEGMENTATION RFM")
    
    if 'client_stats' in results and 'Recence_Jours' in client_stats.columns:
        # Calcul des scores RFM (1-5, 5 = meilleur)
        client_stats['R_Score'] = pd.qcut(client_stats['Recence_Jours'], q=5, labels=[5,4,3,2,1], duplicates='drop')
        client_stats['F_Score'] = pd.qcut(client_stats['Nb_Commandes'], q=5, labels=[1,2,3,4,5], duplicates='drop')
        client_stats['M_Score'] = pd.qcut(client_stats['CA_Total'], q=5, labels=[1,2,3,4,5], duplicates='drop')
        
        # Score RFM global
        client_stats['RFM_Score'] = (client_stats['R_Score'].astype(int) + 
                                      client_stats['F_Score'].astype(int) + 
                                      client_stats['M_Score'].astype(int))
        
        # Segmentation
        def classify_rfm(score):
            if score >= 13:
                return 'Champions'
            elif score >= 10:
                return 'Loyal'
            elif score >= 7:
                return 'Potentiel'
            else:
                return 'Risque'
        
        client_stats['Segment_RFM'] = client_stats['RFM_Score'].apply(classify_rfm)
        
        # Résumé par segment
        rfm_summary = client_stats.groupby('Segment_RFM').agg({
            'CA_Total': ['sum', 'count'],
            'Nb_Commandes': 'mean',
            'Recence_Jours': 'mean'
        })
        rfm_summary.columns = ['CA_Total', 'Nb_Clients', 'Freq_Moyenne', 'Recence_Moyenne']
        
        print(f"\n   Répartition des clients par segment RFM :")
        for segment in ['Champions', 'Loyal', 'Potentiel', 'Risque']:
            if segment in rfm_summary.index:
                row = rfm_summary.loc[segment]
                print(f"   • {segment:12s} : {row['Nb_Clients']:>5,.0f} clients | CA: {row['CA_Total']:>12,.0f}€ | Fréq: {row['Freq_Moyenne']:.1f} | Récence: {row['Recence_Moyenne']:.0f}j")
        
        results['rfm_summary'] = rfm_summary
        results['client_stats'] = client_stats  # Mise à jour avec scores RFM
    
    # ─────────────────────────────────────────────────────────────────────
    # 4. ANALYSE PAR PAYS
    # ─────────────────────────────────────────────────────────────────────
    
    print("\n📊 4. RÉPARTITION PAR PAYS")
    
    if 'Country' in df_final.columns:
        country_client_stats = df_final.groupby('Country').agg({
            'Cpt Client': 'nunique',
            'Montant': 'sum'
        }).sort_values('Montant', ascending=False)
        
        country_client_stats.columns = ['Nb_Clients', 'CA_Total']
        country_client_stats['CA_par_Client'] = country_client_stats['CA_Total'] / country_client_stats['Nb_Clients']
        
        print(f"\n   Top 10 pays par nombre de clients :")
        for idx, row in country_client_stats.head(10).iterrows():
            print(f"   • {idx:15s} : {row['Nb_Clients']:>5,.0f} clients | CA: {row['CA_Total']:>12,.0f}€ | CA/client: {row['CA_par_Client']:>10,.0f}€")
        
        results['country_client_stats'] = country_client_stats
    
    print("\n" + "="*100)
    
    return results


def generate_client_analysis(df_final: pd.DataFrame) -> dict:
    """
    Wrapper pour l'analyse clients - utilisé dans les views
    
    Args:
        df_final: DataFrame nettoyé
    
    Returns:
        dict avec l'analyse complète des clients
    """
    return analyze_clients(df_final)
