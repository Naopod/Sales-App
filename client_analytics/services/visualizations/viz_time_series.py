"""
Visualisations pour le sous-onglet SÉRIE TEMPORELLE
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from statsmodels.tsa.seasonal import STL


def create_stl_decomposition_plot(df_agg):
    """
    Crée le graphique de décomposition STL (Tendance, Saisonnalité, Résidus)
    
    Args:
        df_agg: DataFrame agrégé avec index temporel et colonne CA_Total
        
    Returns:
        str: HTML du graphique Plotly
    """
    if 'CA_Total' not in df_agg.columns or len(df_agg) < 12:
        return None
        
    try:
        # STL Decomposition
        stl = STL(df_agg['CA_Total'], seasonal=13)
        result = stl.fit()
        
        # Création du graphique avec subplots
        fig = make_subplots(
            rows=4, cols=1, 
            shared_xaxes=True,
            subplot_titles=('Série originale', 'Tendance', 'Saisonnalité', 'Résidus'),
            vertical_spacing=0.08
        )
        
        # Série originale
        fig.add_trace(
            go.Scatter(x=df_agg.index.astype(str), y=df_agg['CA_Total'], 
                      name='Original', line=dict(color='#2E86AB', width=2)),
            row=1, col=1
        )
        
        # Tendance
        fig.add_trace(
            go.Scatter(x=df_agg.index.astype(str), y=result.trend, 
                      name='Tendance', line=dict(color='#A23B72', width=2)),
            row=2, col=1
        )
        
        # Saisonnalité
        fig.add_trace(
            go.Scatter(x=df_agg.index.astype(str), y=result.seasonal, 
                      name='Saisonnalité', line=dict(color='#F18F01', width=2)),
            row=3, col=1
        )
        
        # Résidus
        fig.add_trace(
            go.Scatter(x=df_agg.index.astype(str), y=result.resid, 
                      name='Résidus', line=dict(color='#C73E1D', width=1)),
            row=4, col=1
        )
        
        # Mise en forme
        fig.update_layout(
            height=800,
            showlegend=False,
            title_text="Décomposition STL du Chiffre d'Affaires",
            title_font=dict(size=16, family='Arial Black'),
            paper_bgcolor='rgba(20, 30, 50, 1)',
            plot_bgcolor='rgba(30, 40, 60, 1)'
        )
        
        fig.update_xaxes(title_text="Période", row=4, col=1)
        fig.update_yaxes(title_text="CA (€)", row=1, col=1)
        fig.update_yaxes(title_text="CA (€)", row=2, col=1)
        fig.update_yaxes(title_text="Amplitude (€)", row=3, col=1)
        fig.update_yaxes(title_text="Résidus (€)", row=4, col=1)
        
        return fig.to_html(full_html=False)
        
    except Exception as e:
        print(f"Erreur lors de la création du graphique STL: {e}")
        return None
