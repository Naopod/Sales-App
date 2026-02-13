"""
Visualisations pour l'onglet CLUSTERING
"""
import pandas as pd
import plotly.express as px
from sklearn.decomposition import PCA


def _make_responsive(fig):
    """Helper pour rendre un graphique Plotly responsive."""
    fig.update_layout(
        autosize=True,
        width=None,
        margin=dict(l=40, r=20, t=60, b=40)
    )
    return fig


def _to_html_responsive(fig):
    """Convertit une figure Plotly en HTML avec config responsive."""
    fig = _make_responsive(fig)
    return fig.to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': True})


def create_clustering_pca_plot(df_client, X, title="Clustering K-Means (PCA 2D)"):
    """
    Crée le graphique de clustering en 2D avec réduction PCA
    
    Args:
        df_client: DataFrame des clients avec colonne 'Cluster' et 'CA_Total'
        X: Array numpy des features normalisées (pour PCA)
        title: Titre du graphique
        
    Returns:
        str: HTML du graphique Plotly
    """
    try:
        # PCA pour visualisation 2D
        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(X)
        
        # Création DataFrame pour plotting
        df_pca = pd.DataFrame({
            'PC1': X_pca[:, 0],
            'PC2': X_pca[:, 1],
            'Cluster': df_client['Cluster'].astype(str),
            'CA_Total': df_client['CA_Total'],
            'Client': df_client['Cpt_Client'] if 'Cpt_Client' in df_client.columns else range(len(df_client))
        })
        
        # Création du scatter plot
        fig = px.scatter(
            df_pca, 
            x='PC1', 
            y='PC2', 
            color='Cluster',
            size='CA_Total',
            hover_data=['Client', 'CA_Total'],
            title=title,
            labels={
                'PC1': f'PC1 ({pca.explained_variance_ratio_[0]:.1%} variance)',
                'PC2': f'PC2 ({pca.explained_variance_ratio_[1]:.1%} variance)',
                'Cluster': 'Cluster',
                'CA_Total': 'CA Total (€)'
            },
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        
        # Mise en forme
        fig.update_layout(
            height=600,
            font=dict(size=12),
            title_font=dict(size=16, family='Arial Black'),
            legend=dict(
                title=dict(text='Cluster', font=dict(size=14)),
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02
            ),
            paper_bgcolor='rgba(20, 30, 50, 1)',
            plot_bgcolor='rgba(30, 40, 60, 1)'
        )
        
        fig.update_traces(marker=dict(line=dict(width=0.5, color='DarkSlateGrey')))
        
        return _to_html_responsive(fig)
        
    except Exception as e:
        print(f"Erreur lors de la création du graphique de clustering: {e}")
        return None


def create_cluster_stats_table(cluster_stats):
    """
    Crée un tableau HTML des statistiques par cluster
    
    Args:
        cluster_stats: DataFrame avec les stats par cluster
        
    Returns:
        str: HTML du tableau
    """
    return cluster_stats.to_html(
        classes='table table-striped table-hover',
        float_format=lambda x: f'{x:,.2f}',
        escape=False
    )
