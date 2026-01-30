"""
Visualisations pour l'onglet ANALYSE PAR PÉRIODES
Graphiques pour les analyses statistiques par mois, trimestre ou année fiscale
"""
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats


def create_correlation_matrix(df, variables):
    """Crée une matrice de corrélation interactive"""
    try:
        fig = go.Figure(data=go.Heatmap(
            z=df[variables].corr().values,
            x=variables,
            y=variables,
            colorscale='RdBu',
            zmid=0,
            text=df[variables].corr().round(2).values,
            texttemplate='%{text}',
            textfont={"size": 12}
        ))
        fig.update_layout(
            title='Matrice de corrélation',
            height=400,
            template='plotly_dark',
            paper_bgcolor='rgba(20, 30, 50, 1)',
            plot_bgcolor='rgba(30, 40, 60, 1)'
        )
        return fig.to_html(full_html=False, include_plotlyjs='cdn')
    except Exception as e:
        print(f"   ⚠️ Erreur matrice corrélation: {e}")
        return None


def create_distribution_plot(df, variable, title=None):
    """Crée un histogramme de distribution"""
    try:
        if title is None:
            title = f'Distribution de {variable}'
        
        fig = px.histogram(
            df,
            x=variable,
            nbins=50,
            title=title,
            labels={variable: variable},
            template='plotly_dark'
        )
        fig.update_layout(
            height=350,
            showlegend=False,
            paper_bgcolor='rgba(20, 30, 50, 1)',
            plot_bgcolor='rgba(30, 40, 60, 1)'
        )
        return fig.to_html(full_html=False, include_plotlyjs='cdn')
    except Exception as e:
        print(f"   ⚠️ Erreur distribution {variable}: {e}")
        return None


def create_top_categories_plot(df, category_col, value_col, n_top=10, title=None):
    """Crée un graphique en barres horizontales des top catégories"""
    try:
        if title is None:
            title = f'Top {n_top} {category_col} par {value_col}'
        
        top_data = df.groupby(category_col)[value_col].sum().nlargest(n_top).sort_values()
        
        fig = px.bar(
            x=top_data.values,
            y=top_data.index,
            orientation='h',
            title=title,
            labels={'x': f'{value_col} (€)', 'y': category_col},
            template='plotly_dark'
        )
        fig.update_layout(
            height=400,
            showlegend=False,
            paper_bgcolor='rgba(20, 30, 50, 1)',
            plot_bgcolor='rgba(30, 40, 60, 1)'
        )
        return fig.to_html(full_html=False, include_plotlyjs='cdn')
    except Exception as e:
        print(f"   ⚠️ Erreur top {category_col}: {e}")
        return None


def create_temporal_aggregation_plot(df, time_col, value_col, granularity='month'):
    """
    Crée un graphique d'agrégation temporelle selon la granularité
    
    Args:
        df: DataFrame
        time_col: Colonne temporelle ('Month', 'Quarter', 'Fiscal_Year_Label')
        value_col: Colonne à agréger (ex: 'Montant')
        granularity: 'month', 'quarter', 'year'
    """
    try:
        # Titres selon la granularité
        titles = {
            'month': 'CA par Mois',
            'quarter': 'CA par Trimestre Fiscal',
            'year': 'CA par Année Fiscale'
        }
        
        agg_data = df.groupby(time_col)[value_col].sum().sort_index()
        
        fig = px.bar(
            x=agg_data.index,
            y=agg_data.values,
            title=titles.get(granularity, 'CA par Période'),
            labels={'x': 'Période', 'y': 'CA (€)'},
            template='plotly_white'
        )
        fig.update_layout(
            height=400,
            showlegend=False,
            paper_bgcolor='rgba(20, 30, 50, 1)',
            plot_bgcolor='rgba(30, 40, 60, 1)'
        )
        return fig.to_html(full_html=False, include_plotlyjs='cdn')
    except Exception as e:
        print(f"   ⚠️ Erreur agrégation temporelle: {e}")
        return None


def create_temporal_evolution_plot(df, time_col, value_col, granularity='month'):
    """
    Crée un graphique d'évolution temporelle (ligne) selon la granularité
    
    Args:
        df: DataFrame
        time_col: Colonne temporelle
        value_col: Colonne à agréger
        granularity: 'month', 'quarter', 'year'
    """
    try:
        titles = {
            'month': 'Évolution Mensuelle du CA',
            'quarter': 'Évolution Trimestrielle du CA',
            'year': 'Évolution Annuelle du CA'
        }
        
        agg_data = df.groupby(time_col)[value_col].sum().sort_index()
        
        fig = px.line(
            x=agg_data.index,
            y=agg_data.values,
            title=titles.get(granularity, 'Évolution du CA'),
            labels={'x': 'Période', 'y': 'CA (€)'},
            template='plotly_dark',
            markers=True
        )
        fig.update_layout(
            height=400,
            showlegend=False,
            paper_bgcolor='rgba(20, 30, 50, 1)',
            plot_bgcolor='rgba(30, 40, 60, 1)'
        )
        return fig.to_html(full_html=False, include_plotlyjs='cdn')
    except Exception as e:
        print(f"   ⚠️ Erreur évolution temporelle: {e}")
        return None


def create_variation_plot(df, time_col, value_col, granularity='month'):
    """
    Crée un graphique de variation (%) période à période
    
    Args:
        df: DataFrame
        time_col: Colonne temporelle
        value_col: Colonne à agréger
        granularity: 'month', 'quarter', 'year'
    """
    try:
        titles = {
            'month': 'Variation Mensuelle du CA (%)',
            'quarter': 'Variation Trimestrielle du CA (%)',
            'year': 'Variation Annuelle du CA (%)'
        }
        
        agg_data = df.groupby(time_col)[value_col].sum().sort_index()
        variation_pct = agg_data.pct_change() * 100
        
        colors = ['red' if v < 0 else 'green' for v in variation_pct.values]
        
        fig = go.Figure(data=[
            go.Bar(
                x=variation_pct.index[1:],  # Exclure la première valeur (NaN)
                y=variation_pct.values[1:],
                marker_color=colors[1:],
                text=variation_pct.round(1).values[1:],
                texttemplate='%{text}%',
                textposition='outside'
            )
        ])
        
        fig.update_layout(
            title=titles.get(granularity, 'Variation du CA (%)'),
            xaxis_title='Période',
            yaxis_title='Variation (%)',
            height=400,
            template='plotly_dark',
            showlegend=False,
            paper_bgcolor='rgba(20, 30, 50, 1)',
            plot_bgcolor='rgba(30, 40, 60, 1)'
        )
        return fig.to_html(full_html=False, include_plotlyjs='cdn')
    except Exception as e:
        print(f"   ⚠️ Erreur variation: {e}")
        return None


def create_qq_plot(df, variable):
    """
    Crée un graphique QQ-plot (Quantile-Quantile) pour tester la normalité
    
    Args:
        df: DataFrame
        variable: Nom de la variable à analyser
    
    Returns:
        HTML du graphique Plotly
    """
    try:
        # Supprimer les NaN
        data = df[variable].dropna()
        
        # Calculer les quantiles théoriques et empiriques
        theoretical_quantiles = stats.probplot(data, dist="norm")[0][0]
        sample_quantiles = stats.probplot(data, dist="norm")[0][1]
        
        # Créer le graphique
        fig = go.Figure()
        
        # Points QQ
        fig.add_trace(go.Scatter(
            x=theoretical_quantiles,
            y=sample_quantiles,
            mode='markers',
            name='Données',
            marker=dict(color='blue', size=5, opacity=0.6)
        ))
        
        # Ligne théorique (y=x)
        min_val = min(theoretical_quantiles.min(), sample_quantiles.min())
        max_val = max(theoretical_quantiles.max(), sample_quantiles.max())
        fig.add_trace(go.Scatter(
            x=[min_val, max_val],
            y=[min_val, max_val],
            mode='lines',
            name='Distribution normale théorique',
            line=dict(color='red', dash='dash')
        ))
        
        fig.update_layout(
            title=f'QQ-Plot - {variable}',
            xaxis_title='Quantiles théoriques (distribution normale)',
            yaxis_title='Quantiles empiriques (données)',
            height=400,
            template='plotly_dark',
            showlegend=True,
            paper_bgcolor='rgba(20, 30, 50, 1)',
            plot_bgcolor='rgba(30, 40, 60, 1)'
        )
        
        return fig.to_html(full_html=False, include_plotlyjs='cdn')
    except Exception as e:
        print(f"   ⚠️ Erreur QQ-plot pour {variable}: {e}")
        return None


def create_normality_test_plot(df, variable):
    """
    Crée un histogramme avec courbe normale théorique superposée
    
    Args:
        df: DataFrame
        variable: Nom de la variable à analyser
    
    Returns:
        HTML du graphique Plotly
    """
    try:
        # Supprimer les NaN
        data = df[variable].dropna()
        
        # Calculer la moyenne et l'écart-type
        mean = data.mean()
        std = data.std()
        
        # Créer l'histogramme
        fig = go.Figure()
        
        # Histogramme des données
        fig.add_trace(go.Histogram(
            x=data,
            name='Données réelles',
            nbinsx=50,
            histnorm='probability density',
            marker_color='lightblue',
            opacity=0.7
        ))
        
        # Courbe normale théorique
        x_range = np.linspace(data.min(), data.max(), 100)
        y_normal = stats.norm.pdf(x_range, mean, std)
        
        fig.add_trace(go.Scatter(
            x=x_range,
            y=y_normal,
            mode='lines',
            name='Distribution normale théorique',
            line=dict(color='red', width=2)
        ))
        
        fig.update_layout(
            title=f'Test de Normalité - {variable}',
            xaxis_title=variable,
            yaxis_title='Densité de probabilité',
            height=400,
            template='plotly_dark',
            showlegend=True,
            bargap=0.1,
            paper_bgcolor='rgba(20, 30, 50, 1)',
            plot_bgcolor='rgba(30, 40, 60, 1)'
        )
        
        return fig.to_html(full_html=False, include_plotlyjs='cdn')
    except Exception as e:
        print(f"   ⚠️ Erreur test normalité pour {variable}: {e}")
        return None


def create_outliers_boxplot(df, variables):
    """
    Crée des boxplots pour visualiser les valeurs aberrantes
    
    Args:
        df: DataFrame
        variables: Liste des variables à analyser
    
    Returns:
        HTML du graphique Plotly
    """
    try:
        fig = go.Figure()
        
        for variable in variables:
            if variable in df.columns:
                data = df[variable].dropna()
                fig.add_trace(go.Box(
                    y=data,
                    name=variable,
                    boxmean='sd',  # Affiche moyenne et écart-type
                    marker_color='lightblue',
                    boxpoints='outliers'  # Affiche uniquement les outliers
                ))
        
        fig.update_layout(
            title='Analyse des Valeurs Aberrantes (Boxplot)',
            yaxis_title='Valeur',
            height=500,
            template='plotly_dark',
            showlegend=True,
            paper_bgcolor='rgba(20, 30, 50, 1)',
            plot_bgcolor='rgba(30, 40, 60, 1)'
        )
        
        return fig.to_html(full_html=False, include_plotlyjs='cdn')
    except Exception as e:
        print(f"   ⚠️ Erreur boxplot outliers: {e}")
        return None


def create_correlation_heatmap_enhanced(df, variables):
    """
    Crée une matrice de corrélation enrichie avec annotations détaillées
    
    Args:
        df: DataFrame
        variables: Liste des variables numériques
    
    Returns:
        HTML du graphique Plotly
    """
    try:
        corr_matrix = df[variables].corr()
        
        # Masquer le triangle supérieur pour plus de clarté
        mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
        corr_masked = corr_matrix.copy()
        corr_masked[mask] = np.nan
        
        fig = go.Figure(data=go.Heatmap(
            z=corr_masked.values,
            x=variables,
            y=variables,
            colorscale='RdBu',
            zmid=0,
            zmin=-1,
            zmax=1,
            text=corr_masked.round(3).values,
            texttemplate='%{text}',
            textfont={"size": 14, "color": "black"},
            colorbar=dict(title="Corrélation")
        ))
        
        fig.update_layout(
            title='Matrice de Corrélation (Triangle inférieur)',
            height=450,
            template='plotly_dark',
            xaxis=dict(side='bottom'),
            yaxis=dict(autorange='reversed'),
            paper_bgcolor='rgba(20, 30, 50, 1)',
            plot_bgcolor='rgba(30, 40, 60, 1)'
        )
        
        return fig.to_html(full_html=False, include_plotlyjs='cdn')
    except Exception as e:
        print(f"   ⚠️ Erreur matrice corrélation enrichie: {e}")
        return None

