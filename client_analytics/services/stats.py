"""
Statistics Service - High Tech 2024
Génère des statistiques descriptives et visualisations basées sur les analyses du notebook
"""
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats as scipy_stats


def generate_statistics(df):
    """
    Génère l'ensemble des analyses statistiques High Tech 2024
    
    Args:
        df: DataFrame pandas contenant les données
        
    Returns:
        dict: Dictionnaire avec les résultats et graphiques
    """
    results = {}
    graphs = {}
    
    print("📊 Génération des analyses statistiques...")
    
    # 1. STATISTIQUES DESCRIPTIVES
    variables_cles = ['Montant', 'Quantité', 'PU Net']
    stats_table = []
    
    for var in variables_cles:
        if var in df.columns:
            stats_table.append({
                'Variable': var,
                'Nombre': f"{df[var].count():,}",
                'Moyenne': f"{df[var].mean():.2f}",
                'Médiane': f"{df[var].median():.2f}",
                'Écart-type': f"{df[var].std():.2f}",
                'Min': f"{df[var].min():.2f}",
                'Max': f"{df[var].max():.2f}",
                'Q1': f"{df[var].quantile(0.25):.2f}",
                'Q3': f"{df[var].quantile(0.75):.2f}"
            })
    
    results['stats_descriptives'] = pd.DataFrame(stats_table).to_html(
        classes='table table-striped table-hover', 
        index=False,
        border=0
    )
    
    # 2. TESTS DE NORMALITÉ (Shapiro-Wilk)
    normalite_tests = []
    for var in variables_cles:
        if var in df.columns and len(df[var].dropna()) > 0:
            sample = df[var].dropna().sample(min(5000, len(df[var].dropna())))
            stat, p_value = scipy_stats.shapiro(sample)
            
            normalite_tests.append({
                'Variable': var,
                'Statistique W': f"{stat:.4f}",
                'p-value': f"{p_value:.4e}",
                'Distribution': '❌ Non normale' if p_value < 0.05 else '✅ Normale'
            })
    
    results['tests_normalite'] = pd.DataFrame(normalite_tests).to_html(
        classes='table table-striped table-hover', 
        index=False,
        border=0,
        escape=False
    )
    
    # 3. DÉTECTION DES VALEURS ABERRANTES (Méthode IQR)
    outliers_info = []
    for var in variables_cles:
        if var in df.columns:
            Q1 = df[var].quantile(0.25)
            Q3 = df[var].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outliers = df[(df[var] < lower_bound) | (df[var] > upper_bound)]
            pct = (len(outliers) / len(df)) * 100
            
            outliers_info.append({
                'Variable': var,
                'Borne inférieure': f"{lower_bound:.2f}",
                'Borne supérieure': f"{upper_bound:.2f}",
                'Nombre d\'outliers': f"{len(outliers):,}",
                'Pourcentage': f"{pct:.2f}%"
            })
    
    results['valeurs_aberrantes'] = pd.DataFrame(outliers_info).to_html(
        classes='table table-striped table-hover', 
        index=False,
        border=0
    )
    
    # 4. GRAPHIQUES
    
    # Distribution du Montant avec boxplot
    if 'Montant' in df.columns:
        fig = make_subplots(
            rows=2, cols=1,
            row_heights=[0.7, 0.3],
            subplot_titles=('Distribution du Montant', 'Boxplot - Détection des outliers'),
            vertical_spacing=0.15
        )
        
        fig.add_trace(
            go.Histogram(x=df['Montant'], nbinsx=50, name='Montant',
                        marker_color='steelblue'),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Box(x=df['Montant'], name='Montant',
                  marker_color='indianred'),
            row=2, col=1
        )
        
        fig.update_layout(
            height=600, 
            showlegend=False, 
            title_text="<b>Analyse du Montant</b>",
            template='plotly_white'
        )
        graphs['dist_montant'] = fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    # Distribution de la Quantité
    if 'Quantité' in df.columns:
        fig = px.histogram(df, x='Quantité', nbins=50, 
                          title='<b>Distribution de la Quantité</b>',
                          marginal='box',
                          color_discrete_sequence=['steelblue'])
        fig.update_layout(height=500, template='plotly_white')
        graphs['dist_quantite'] = fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    # Distribution du PU Net
    if 'PU Net' in df.columns:
        fig = px.histogram(df, x='PU Net', nbins=50,
                          title='<b>Distribution du Prix Unitaire Net</b>',
                          marginal='box',
                          color_discrete_sequence=['mediumseagreen'])
        fig.update_layout(height=500, template='plotly_white')
        graphs['dist_pu_net'] = fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    # Matrice de corrélation
    if all(col in df.columns for col in variables_cles):
        corr = df[variables_cles].corr()
        
        fig = go.Figure(data=go.Heatmap(
            z=corr.values,
            x=corr.columns,
            y=corr.columns,
            text=np.round(corr.values, 2),
            texttemplate='%{text}',
            textfont={"size": 14, "color": "white"},
            colorscale='RdBu_r',
            zmid=0,
            zmin=-1,
            zmax=1
        ))
        
        fig.update_layout(
            title='<b>Matrice de Corrélation</b>',
            height=500,
            template='plotly_white',
            xaxis_title='',
            yaxis_title=''
        )
        graphs['correlation'] = fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    # Top 10 Pays par CA
    if 'Country' in df.columns and 'Montant' in df.columns:
        ca_par_pays = df.groupby('Country')['Montant'].sum().sort_values(ascending=False).head(10)
        
        fig = go.Figure(data=[
            go.Bar(x=ca_par_pays.index, y=ca_par_pays.values,
                  marker_color='indianred',
                  text=ca_par_pays.values,
                  texttemplate='%{text:,.0f}€',
                  textposition='outside')
        ])
        fig.update_layout(
            title='<b>Top 10 Pays par Chiffre d\'Affaires</b>',
            xaxis_title='Pays',
            yaxis_title='CA (€)',
            height=500,
            template='plotly_white'
        )
        graphs['top_pays'] = fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    # Top 10 Familles de produits
    if 'Famille' in df.columns and 'Montant' in df.columns:
        ca_par_famille = df.groupby('Famille')['Montant'].sum().sort_values(ascending=False).head(10)
        
        fig = go.Figure(data=[
            go.Bar(x=ca_par_famille.values, y=ca_par_famille.index,
                  orientation='h',
                  marker_color='steelblue',
                  text=ca_par_famille.values,
                  texttemplate='%{text:,.0f}€',
                  textposition='outside')
        ])
        fig.update_layout(
            title='<b>Top 10 Familles de Produits par CA</b>',
            xaxis_title='CA (€)',
            yaxis_title='Famille',
            height=500,
            template='plotly_white'
        )
        graphs['top_familles'] = fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    # Evolution par Quarter
    if 'Quarter' in df.columns and 'Montant' in df.columns:
        ca_par_quarter = df.groupby('Quarter')['Montant'].sum()
        
        fig = go.Figure(data=[
            go.Scatter(x=ca_par_quarter.index, y=ca_par_quarter.values,
                      mode='lines+markers',
                      marker=dict(size=12, color='steelblue'),
                      line=dict(width=3, color='steelblue'),
                      text=ca_par_quarter.values,
                      texttemplate='%{text:,.0f}€',
                      textposition='top center')
        ])
        fig.update_layout(
            title='<b>Évolution du CA par Trimestre 2024</b>',
            xaxis_title='Trimestre',
            yaxis_title='CA (€)',
            height=500,
            template='plotly_white'
        )
        graphs['evolution_quarter'] = fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    # Informations générales
    results['total_transactions'] = f"{len(df):,}"
    results['ca_total'] = f"{df['Montant'].sum():,.2f} €" if 'Montant' in df.columns else "N/A"
    results['nb_clients'] = f"{df['Cpt Client'].nunique():,}" if 'Cpt Client' in df.columns else "N/A"
    results['nb_produits'] = f"{df['Famille'].nunique():,}" if 'Famille' in df.columns else "N/A"
    results['panier_moyen'] = f"{df['Montant'].mean():.2f} €" if 'Montant' in df.columns else "N/A"
    
    print("✅ Analyses statistiques générées")
    
    return {
        'results': results,
        'graphs': graphs
    }


# Fonctions de compatibilité pour l'ancien code
def create_histogram(df, column):
    """Create histogram for a numeric column"""
    if column not in df.columns or not pd.api.types.is_numeric_dtype(df[column]):
        return None
    
    fig = px.histogram(
        df,
        x=column,
        title=f'Distribution de {column}',
        labels={column: column, 'count': 'Fréquence'},
        nbins=30
    )
    fig.update_layout(
        template='plotly_white',
        height=400,
        showlegend=False
    )
    return fig.to_html(full_html=False, include_plotlyjs='cdn')


def create_bar_chart(df, column, top_n=10):
    """Create bar chart for a categorical column"""
    if column not in df.columns:
        return None
    
    value_counts = df[column].value_counts().head(top_n)
    
    fig = px.bar(
        x=value_counts.index,
        y=value_counts.values,
        title=f'Top {top_n} valeurs de {column}',
        labels={'x': column, 'y': 'Nombre'}
    )
    fig.update_layout(
        template='plotly_white',
        height=400,
        showlegend=False
    )
    return fig.to_html(full_html=False, include_plotlyjs='cdn')


def create_correlation_heatmap(df):
    """Create correlation heatmap for numeric columns"""
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    
    if len(numeric_cols) < 2:
        return None
    
    corr_matrix = df[numeric_cols].corr()
    
    fig = px.imshow(
        corr_matrix,
        text_auto='.2f',
        aspect='auto',
        title='Matrice de Corrélation',
        color_continuous_scale='RdBu_r',
        zmin=-1,
        zmax=1
    )
    fig.update_layout(
        template='plotly_white',
        height=600
    )
    return fig.to_html(full_html=False, include_plotlyjs='cdn')


def create_all_histograms(df):
    """Create histograms for all numeric columns"""
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    
    if len(numeric_cols) == 0:
        return None
    
    plots = {}
    for col in numeric_cols:
        plots[col] = create_histogram(df, col)
    
    return plots


def create_all_bar_charts(df, top_n=10):
    """Create bar charts for all categorical columns"""
    categorical_cols = df.select_dtypes(exclude=[np.number]).columns
    
    if len(categorical_cols) == 0:
        return None
    
    plots = {}
    for col in categorical_cols:
        if df[col].nunique() < 50:  # Only for columns with reasonable number of categories
            plots[col] = create_bar_chart(df, col, top_n)
    
    return plots


def get_basic_stats(df, column):
    """Get basic statistics for a column"""
    if column not in df.columns:
        return None
    
    stats = {}
    
    if pd.api.types.is_numeric_dtype(df[column]):
        stats = {
            'count': int(df[column].count()),
            'mean': float(df[column].mean()),
            'std': float(df[column].std()),
            'min': float(df[column].min()),
            'q25': float(df[column].quantile(0.25)),
            'median': float(df[column].median()),
            'q75': float(df[column].quantile(0.75)),
            'max': float(df[column].max()),
            'missing': int(df[column].isnull().sum())
        }
    else:
        stats = {
            'count': int(df[column].count()),
            'unique': int(df[column].nunique()),
            'top': str(df[column].mode()[0]) if len(df[column].mode()) > 0 else 'N/A',
            'freq': int(df[column].value_counts().iloc[0]) if len(df[column]) > 0 else 0,
            'missing': int(df[column].isnull().sum())
        }
    
    return stats
