"""
Clustering Service - High Tech 2024
K-Means clustering avec analyse RFM et visualisation PCA
"""
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime


def create_client_dataset(df):
    """
    Crée le dataset client agrégé à partir des transactions
    Comme dans le notebook High Tech 2024
    
    Args:
        df: DataFrame des transactions
        
    Returns:
        DataFrame client avec métriques agrégées
    """
    print("📊 Création du dataset client...")
    
    # Agrégation par client
    df_client = df.groupby('Cpt Client').agg({
        'Montant': ['sum', 'mean', 'count'],
        'Quantité': 'sum',
        'Date Cde': ['min', 'max'],
        'Country': 'first',
        'Famille': 'nunique'
    }).reset_index()
    
    # Renommer les colonnes
    df_client.columns = ['Cpt_Client', 'CA_Total', 'CA_Moyen', 'Nb_Commandes', 
                         'Qty_Total', 'Date_Premiere_Cde', 'Date_Derniere_Cde', 
                         'Country', 'Nb_Familles_Distinctes']
    
    # Calcul Recency (jours depuis dernière commande)
    date_reference = df['Date Cde'].max()
    df_client['Recency'] = (date_reference - df_client['Date_Derniere_Cde']).dt.days
    
    # Calcul Frequency (nombre de commandes)
    df_client['Frequency'] = df_client['Nb_Commandes']
    
    # Calcul Monetary (CA total)
    df_client['Monetary'] = df_client['CA_Total']
    
    # Panier moyen
    df_client['Panier_Moyen'] = df_client['CA_Total'] / df_client['Nb_Commandes']
    
    print(f"✅ Dataset client créé : {len(df_client)} clients")
    
    return df_client


def perform_rfm_analysis(df_client):
    """
    Analyse RFM (Recency, Frequency, Monetary)
    
    Args:
        df_client: DataFrame client avec Recency, Frequency, Monetary
        
    Returns:
        dict avec résultats RFM et graphiques
    """
    print("📊 Analyse RFM...")
    
    results = {}
    graphs = {}
    
    # Créer les scores RFM (quintiles)
    df_client['R_Score'] = pd.qcut(df_client['Recency'], q=5, labels=[5,4,3,2,1], duplicates='drop')
    df_client['F_Score'] = pd.qcut(df_client['Frequency'].rank(method='first'), q=5, labels=[1,2,3,4,5], duplicates='drop')
    df_client['M_Score'] = pd.qcut(df_client['Monetary'].rank(method='first'), q=5, labels=[1,2,3,4,5], duplicates='drop')
    
    # Convertir en numérique
    df_client['R_Score'] = df_client['R_Score'].astype(int)
    df_client['F_Score'] = df_client['F_Score'].astype(int)
    df_client['M_Score'] = df_client['M_Score'].astype(int)
    
    # Score RFM global
    df_client['RFM_Score'] = df_client['R_Score'] + df_client['F_Score'] + df_client['M_Score']
    
    # Segmentation RFM
    def rfm_segment(row):
        r, f, m = row['R_Score'], row['F_Score'], row['M_Score']
        
        if r >= 4 and f >= 4 and m >= 4:
            return 'Champions'
        elif r >= 3 and f >= 3 and m >= 3:
            return 'Fidèles'
        elif r >= 4 and f <= 2:
            return 'Nouveaux'
        elif r <= 2 and f >= 3:
            return 'À risque'
        elif r <= 2 and f <= 2:
            return 'Perdus'
        else:
            return 'Potentiels'
    
    df_client['Segment_RFM'] = df_client.apply(rfm_segment, axis=1)
    
    # Statistiques par segment
    segment_stats = df_client.groupby('Segment_RFM').agg({
        'Cpt_Client': 'count',
        'CA_Total': 'sum',
        'CA_Moyen': 'mean',
        'Recency': 'mean',
        'Frequency': 'mean',
        'Monetary': 'mean'
    }).round(2)
    
    segment_stats.columns = ['Nb Clients', 'CA Total', 'CA Moyen', 'Recency Moy', 'Frequency Moy', 'Monetary Moy']
    segment_stats = segment_stats.sort_values('CA Total', ascending=False)
    
    results['segment_stats_html'] = segment_stats.to_html(classes='table table-striped table-hover', border=0)
    
    # Graphique de distribution des segments
    segment_counts = df_client['Segment_RFM'].value_counts()
    
    fig = go.Figure(data=[
        go.Bar(x=segment_counts.index, y=segment_counts.values,
              marker_color=['#2ecc71', '#3498db', '#f39c12', '#e74c3c', '#95a5a6', '#9b59b6'],
              text=segment_counts.values,
              texttemplate='%{text}',
              textposition='outside')
    ])
    fig.update_layout(
        title='<b>Distribution des Segments RFM</b>',
        xaxis_title='Segment',
        yaxis_title='Nombre de clients',
        height=500,
        template='plotly_white'
    )
    graphs['segment_distribution'] = fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    # Graphique RFM 3D (bubble chart)
    fig = px.scatter_3d(
        df_client,
        x='Recency',
        y='Frequency',
        z='Monetary',
        color='Segment_RFM',
        size='CA_Total',
        hover_data=['Cpt_Client', 'CA_Total'],
        title='<b>Analyse RFM 3D</b>',
        color_discrete_map={
            'Champions': '#2ecc71',
            'Fidèles': '#3498db',
            'Nouveaux': '#f39c12',
            'À risque': '#e74c3c',
            'Perdus': '#95a5a6',
            'Potentiels': '#9b59b6'
        }
    )
    fig.update_layout(height=600, template='plotly_white')
    graphs['rfm_3d'] = fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    # Distribution RFM Score
    fig = px.histogram(df_client, x='RFM_Score', nbins=15,
                      title='<b>Distribution du Score RFM</b>',
                      color='Segment_RFM',
                      color_discrete_map={
                          'Champions': '#2ecc71',
                          'Fidèles': '#3498db',
                          'Nouveaux': '#f39c12',
                          'À risque': '#e74c3c',
                          'Perdus': '#95a5a6',
                          'Potentiels': '#9b59b6'
                      })
    fig.update_layout(height=500, template='plotly_white')
    graphs['rfm_score_dist'] = fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    print("✅ Analyse RFM complétée")
    
    return {
        'df_client': df_client,
        'results': results,
        'graphs': graphs
    }


def perform_clustering(df, feature_columns, n_clusters=3, standardize=True):
    """
    Perform K-Means clustering
    
    Args:
        df: pandas.DataFrame
        feature_columns: list of column names to use
        n_clusters: number of clusters
        standardize: whether to standardize features
        
    Returns:
        dict with clustering results
    """
    try:
        # Prepare data - only numeric columns
        X = df[feature_columns].copy()
        
        # Check if all columns are numeric
        non_numeric = X.select_dtypes(exclude=[np.number]).columns.tolist()
        if non_numeric:
            return {
                'success': False,
                'error': f"Les colonnes suivantes ne sont pas numériques: {', '.join(non_numeric)}"
            }
        
        # Remove rows with missing values
        X_clean = X.dropna()
        
        if len(X_clean) < n_clusters:
            return {
                'success': False,
                'error': f"Pas assez de lignes valides ({len(X_clean)}) pour {n_clusters} clusters"
            }
        
        # Standardize if requested
        if standardize:
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X_clean)
        else:
            X_scaled = X_clean.values
        
        # Perform K-Means
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(X_scaled)
        
        # Calculate metrics
        inertia = float(kmeans.inertia_)
        
        silhouette = None
        if n_clusters > 1 and len(X_clean) > n_clusters:
            try:
                silhouette = float(silhouette_score(X_scaled, cluster_labels))
            except:
                silhouette = None
        
        # PCA for visualization
        pca = PCA(n_components=2, random_state=42)
        X_pca = pca.fit_transform(X_scaled)
        
        # Create visualization dataframe
        viz_df = pd.DataFrame({
            'PC1': X_pca[:, 0],
            'PC2': X_pca[:, 1],
            'Cluster': cluster_labels.astype(str)
        })
        
        # Create PCA plot
        pca_plot_html = create_pca_plot(viz_df, pca)
        
        # Calculate cluster sizes
        unique, counts = np.unique(cluster_labels, return_counts=True)
        cluster_sizes = [
            {'cluster': int(u), 'size': int(c)}
            for u, c in zip(unique, counts)
        ]
        
        # Calculate centroids in original feature space
        centroids_original = []
        if standardize:
            centroids_scaled = kmeans.cluster_centers_
            centroids_unscaled = scaler.inverse_transform(centroids_scaled)
        else:
            centroids_unscaled = kmeans.cluster_centers_
        
        for i, centroid in enumerate(centroids_unscaled):
            centroid_dict = {'cluster': i}
            for j, col in enumerate(feature_columns):
                centroid_dict[col] = float(centroid[j])
            centroids_original.append(centroid_dict)
        
        # Add cluster labels to original dataframe indices
        cluster_mapping = pd.Series(cluster_labels, index=X_clean.index)
        
        results = {
            'success': True,
            'n_clusters': n_clusters,
            'inertia': inertia,
            'silhouette': silhouette,
            'cluster_sizes': cluster_sizes,
            'centroids': centroids_original,
            'pca_plot_html': pca_plot_html,
            'pca_variance_explained': [float(v) for v in pca.explained_variance_ratio_],
            'cluster_labels': cluster_labels.tolist(),
            'valid_indices': X_clean.index.tolist(),
            'feature_columns': feature_columns,
            'standardized': standardize
        }
        
        return results
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def create_pca_plot(viz_df, pca):
    """Create PCA scatter plot colored by cluster"""
    var_explained = pca.explained_variance_ratio_
    
    fig = px.scatter(
        viz_df,
        x='PC1',
        y='PC2',
        color='Cluster',
        title='Visualisation des Clusters (PCA 2D)',
        labels={
            'PC1': f'PC1 ({var_explained[0]:.1%} variance)',
            'PC2': f'PC2 ({var_explained[1]:.1%} variance)',
            'Cluster': 'Cluster'
        }
    )
    
    fig.update_layout(
        template='plotly_white',
        height=500,
        legend_title_text='Cluster'
    )
    
    return fig.to_html(full_html=False, include_plotlyjs='cdn')


def export_clustering_results(df, cluster_labels, valid_indices):
    """
    Add cluster labels to dataframe for export
    
    Args:
        df: original pandas.DataFrame
        cluster_labels: numpy array of cluster labels
        valid_indices: indices of rows that were clustered
        
    Returns:
        pandas.DataFrame with cluster column
    """
    df_export = df.copy()
    
    # Initialize cluster column with NaN
    df_export['cluster'] = np.nan
    
    # Assign cluster labels to valid indices
    df_export.loc[valid_indices, 'cluster'] = cluster_labels
    
    return df_export


def calculate_cluster_statistics(df, feature_columns, cluster_labels, valid_indices):
    """Calculate statistics for each cluster"""
    df_with_clusters = df.copy()
    df_with_clusters.loc[valid_indices, 'cluster'] = cluster_labels
    
    cluster_stats = []
    
    for cluster_id in sorted(df_with_clusters['cluster'].dropna().unique()):
        cluster_data = df_with_clusters[df_with_clusters['cluster'] == cluster_id]
        
        stats = {'cluster': int(cluster_id), 'size': len(cluster_data)}
        
        for col in feature_columns:
            if col in cluster_data.columns:
                stats[f'{col}_mean'] = float(cluster_data[col].mean())
                stats[f'{col}_std'] = float(cluster_data[col].std())
        
        cluster_stats.append(stats)
    
    return cluster_stats
