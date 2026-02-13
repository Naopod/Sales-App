"""
Visualisations pour le sous-onglet GÉOGRAPHIQUE
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd


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


def create_geographic_ca_chart(stats_pays):
    """
    Crée un graphique du CA par pays
    
    Args:
        stats_pays: DataFrame avec CA par pays
        
    Returns:
        str: HTML du graphique Plotly
    """
    if stats_pays is None or len(stats_pays) == 0:
        return None
    
    try:
        # Prendre top 15 pays
        top_countries = stats_pays.nlargest(15, 'CA_Total')
        
        # Couleurs par classification
        color_map = {
            'Excellence': '#10b981',
            'Performant': '#3b82f6',
            'Moyen': '#f59e0b',
            'Faible': '#ef4444'
        }
        
        colors = [color_map.get(c, '#6b7280') for c in top_countries['Classification']]
        
        fig = go.Figure(data=[
            go.Bar(
                y=top_countries.index,
                x=top_countries['CA_Total'],
                orientation='h',
                marker_color=colors,
                text=top_countries['CA_Total'].apply(lambda x: f'{x:,.0f}€'),
                textposition='outside',
                hovertemplate='<b>%{y}</b><br>CA: %{x:,.0f}€<br>Classification: %{customdata}<extra></extra>',
                customdata=top_countries['Classification']
            )
        ])
        
        fig.update_layout(
            title="Top 15 Pays par Chiffre d'Affaires",
            xaxis_title="Chiffre d'Affaires (€)",
            yaxis_title="Pays",
            height=600,
            showlegend=False
        )
        
        return _to_html_responsive(fig)
        
    except Exception as e:
        print(f"Erreur lors de la création du graphique géographique: {e}")
        return None


def create_zone_performance_chart(stats_zone):
    """
    Crée un graphique de performance par zone
    
    Args:
        stats_zone: DataFrame avec stats par zone
        
    Returns:
        str: HTML du graphique Plotly
    """
    if stats_zone is None or len(stats_zone) == 0:
        return None
    
    try:
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=("CA par Zone", "Nombre de Clients par Zone"),
            specs=[[{"type": "bar"}, {"type": "bar"}]]
        )
        
        # CA par zone
        fig.add_trace(
            go.Bar(
                x=stats_zone.index,
                y=stats_zone['CA_Total'],
                name='CA Total',
                marker_color='#3b82f6',
                text=stats_zone['CA_Total'].apply(lambda x: f'{x:,.0f}€'),
                textposition='outside',
                hovertemplate='<b>%{x}</b><br>CA: %{y:,.0f}€<extra></extra>'
            ),
            row=1, col=1
        )
        
        # Clients par zone
        fig.add_trace(
            go.Bar(
                x=stats_zone.index,
                y=stats_zone['Nb_Clients'],
                name='Nb Clients',
                marker_color='#10b981',
                text=stats_zone['Nb_Clients'],
                textposition='outside',
                hovertemplate='<b>%{x}</b><br>Clients: %{y}<extra></extra>'
            ),
            row=1, col=2
        )
        
        fig.update_xaxes(title_text="Zone", row=1, col=1)
        fig.update_xaxes(title_text="Zone", row=1, col=2)
        fig.update_yaxes(title_text="CA (€)", row=1, col=1)
        fig.update_yaxes(title_text="Nombre de Clients", row=1, col=2)
        
        fig.update_layout(
            height=500,
            showlegend=False
        )
        
        return _to_html_responsive(fig)
        
    except Exception as e:
        print(f"Erreur lors de la création du graphique par zone: {e}")
        return None


def create_classification_chart(stats_pays):
    """
    Crée un graphique de répartition par classification
    
    Args:
        stats_pays: DataFrame avec Classification
        
    Returns:
        str: HTML du graphique Plotly
    """
    if stats_pays is None or 'Classification' not in stats_pays.columns:
        return None
    
    try:
        # Compter les pays par classification
        classif_counts = stats_pays['Classification'].value_counts()
        
        # Couleurs
        color_map = {
            'Excellence': '#10b981',
            'Performant': '#3b82f6',
            'Moyen': '#f59e0b',
            'Faible': '#ef4444'
        }
        
        colors = [color_map.get(c, '#6b7280') for c in classif_counts.index]
        
        # Créer un donut chart
        fig = go.Figure(data=[
            go.Pie(
                labels=classif_counts.index,
                values=classif_counts.values,
                hole=0.4,
                marker_colors=colors,
                textinfo='label+value+percent',
                hovertemplate='<b>%{label}</b><br>Pays: %{value}<br>%{percent}<extra></extra>'
            )
        ])
        
        fig.update_layout(
            title="Répartition des Pays par Classification",
            height=400
        )
        
        return _to_html_responsive(fig)
        
    except Exception as e:
        print(f"Erreur lors de la création du graphique de classification: {e}")
        return None


def create_score_distribution_chart(stats_pays):
    """
    Crée un histogramme de distribution des scores
    
    Args:
        stats_pays: DataFrame avec Score_Global
        
    Returns:
        str: HTML du graphique Plotly
    """
    if stats_pays is None or 'Score_Global' not in stats_pays.columns:
        return None
    
    try:
        fig = go.Figure(data=[
            go.Histogram(
                x=stats_pays['Score_Global'],
                nbinsx=20,
                marker_color='#8b5cf6',
                hovertemplate='Score: %{x:.1f}<br>Pays: %{y}<extra></extra>'
            )
        ])
        
        # Ajouter médiane
        median_score = stats_pays['Score_Global'].median()
        fig.add_vline(x=median_score, line_dash="dash", line_color="red",
                     annotation_text=f"Médiane: {median_score:.1f}")
        
        fig.update_layout(
            title="Distribution des Scores Globaux",
            xaxis_title="Score Global",
            yaxis_title="Nombre de Pays",
            height=400
        )
        
        return _to_html_responsive(fig)
        
    except Exception as e:
        print(f"Erreur lors de la création de l'histogramme des scores: {e}")
        return None
