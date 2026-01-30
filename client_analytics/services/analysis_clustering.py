"""
Service pour l'onglet CLUSTERING
Clustering K-Means avec analyse RFM et visualisation PCA
AUTONOME - Ne dépend d'aucun autre fichier de services
"""
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from datetime import datetime

# Import visualizations
from .visualizations.viz_clustering import create_clustering_pca_plot


def create_client_dataset(df):
    """Crée le dataset client agrégé"""
    df_client = df.groupby('Cpt Client').agg({
        'Montant': ['sum', 'mean', 'count'],
        'Quantité': 'sum',
        'Date Cde': ['min', 'max'],
        'Country': 'first'
    }).reset_index()
    
    df_client.columns = ['Cpt_Client', 'CA_Total', 'CA_Moyen', 'Nb_Commandes', 
                         'Qty_Total', 'Date_Premiere_Cde', 'Date_Derniere_Cde', 'Country']
    
    date_reference = df['Date Cde'].max()
    df_client['Recency'] = (date_reference - df_client['Date_Derniere_Cde']).dt.days
    df_client['Frequency'] = df_client['Nb_Commandes']
    df_client['Monetary'] = df_client['CA_Total']
    df_client['Panier_Moyen'] = df_client['CA_Total'] / df_client['Nb_Commandes']
    
    return df_client


def perform_kmeans_clustering(df_client, n_clusters=4, features=['Recency', 'Frequency', 'Monetary']):
    """Effectue le clustering K-Means"""
    # Normalisation
    scaler = StandardScaler()
    X = scaler.fit_transform(df_client[features])
    
    # K-Means
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    df_client['Cluster'] = kmeans.fit_predict(X)
    
    # Silhouette score
    silhouette = silhouette_score(X, df_client['Cluster'])
    
    return df_client, silhouette, X


def generate_clustering_analysis(df):
    """
    Génère l'analyse de clustering complète avec K-Means et PCA
    
    Returns:
        dict: {
            'results': dict avec statistiques par cluster,
            'graphs': dict avec graphiques HTML,
            'kpis': dict avec métriques globales
        }
    """
    print("🎯 Génération de l'analyse de clustering...")
    
    results = {}
    graphs = {}
    kpis = {}
    
    # Création dataset client
    df_client = create_client_dataset(df)
    
    # Clustering
    df_client, silhouette, X = perform_kmeans_clustering(df_client, n_clusters=4)
    
    # Stats par cluster
    cluster_stats = df_client.groupby('Cluster').agg({
        'CA_Total': ['mean', 'sum', 'count'],
        'Recency': 'mean',
        'Frequency': 'mean',
        'Monetary': 'mean'
    }).round(2)
    
    results['cluster_stats'] = cluster_stats.to_dict()
    kpis['silhouette_score'] = float(silhouette)
    kpis['nb_clusters'] = 4
    
    # PCA pour visualisation - utilise la fonction de visualizations
    clustering_plot = create_clustering_pca_plot(df_client, X)
    if clustering_plot:
        graphs['clustering_pca'] = clustering_plot
    
    return {'results': results, 'graphs': graphs, 'kpis': kpis}


def generate_clustering_tab_analysis(df):
    """
    Génère l'analyse complète pour l'onglet Clustering
    
    Args:
        df: DataFrame des transactions
    
    Returns:
        dict avec l'analyse de clustering complète
    """
    print("📊 Génération de l'analyse de clustering...")
    
    # Utilise la fonction complète de clustering
    return generate_clustering_analysis(df)
