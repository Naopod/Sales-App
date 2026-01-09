"""
Service d'Analyse Statistique Complète - High Tech 2024
Reproduit TOUTES les analyses du notebook avec graphiques
"""
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats as scipy_stats
import matplotlib
matplotlib.use('Agg')  # Backend non-interactif pour Django
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64


def generate_complete_statistics(df):
    """
    Génère l'analyse statistique COMPLÈTE comme dans le notebook
    
    Returns:
        dict: {
            'results': dict avec tous les tableaux HTML,
            'graphs': dict avec tous les graphiques HTML,
            'kpis': dict avec les KPIs principaux
        }
    """
    results = {}
    graphs = {}
    kpis = {}
    
    print("📊 Génération de l'analyse statistique complète...")
    
    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 1 : TRAITEMENT DES DONNÉES (NETTOYAGE COMPLET)
    # ═══════════════════════════════════════════════════════════════════
    
    print("\n   🧹 Étape 1 : Nettoyage des données...")
    
    lignes_initiales = len(df)
    print(f"      📊 Lignes initiales : {lignes_initiales:,}")
    
    # 1. Supprimer les lignes avec Quantité = 0 ou négative
    qty_zero = 0
    qty_negative = 0
    if 'Quantité' in df.columns:
        qty_zero = (df['Quantité'] == 0).sum()
        qty_negative = (df['Quantité'] < 0).sum()
        df = df[(df['Quantité'] != 0) & (df['Quantité'] >= 0)].copy()
        if qty_zero > 0:
            print(f"      ❌ Supprimé {qty_zero:,} lignes avec Quantité = 0")
        if qty_negative > 0:
            print(f"      ❌ Supprimé {qty_negative:,} lignes avec Quantité négative")
    
    # 2. Supprimer les lignes avec Montant = 0 ou négatif
    montant_zero = 0
    montant_negative = 0
    if 'Montant' in df.columns:
        montant_zero = (df['Montant'] == 0).sum()
        montant_negative = (df['Montant'] < 0).sum()
        df = df[(df['Montant'] != 0) & (df['Montant'] >= 0)].copy()
        if montant_zero > 0:
            print(f"      ❌ Supprimé {montant_zero:,} lignes avec Montant = 0")
        if montant_negative > 0:
            print(f"      ❌ Supprimé {montant_negative:,} lignes avec Montant négatif")
    
    # 3. Recalculer PU Net si nécessaire
    if 'Montant' in df.columns and 'Quantité' in df.columns:
        if 'PU Net' not in df.columns or df['PU Net'].isna().sum() > 0:
            df['PU Net'] = df['Montant'] / df['Quantité']
            print(f"      ✅ Recalculé PU Net (Montant / Quantité)")
    
    # 4. Extraction du pays depuis Cpt Client si Country n'existe pas
    if 'Country' not in df.columns and 'Cpt Client' in df.columns:
        # Mapping des codes pays
        country_mapping = {
            'FR': 'FR', 'DE': 'DE', 'ES': 'ES', 'IT': 'IT', 'GB': 'GB',
            'CH': 'CH', 'NL': 'NL', 'PT': 'PT', 'AT': 'AT', 'BE': 'BE',
            'AE': 'AE', 'AU': 'AU', 'BG': 'BG', 'BR': 'BR', 'CA': 'CA',
            'CL': 'CL', 'CR': 'CR', 'CZ': 'CZ', 'DK': 'DK', 'GR': 'GR',
            'HR': 'HR', 'HU': 'HU', 'IE': 'IE', 'IN': 'IN', 'LT': 'LT',
            'LU': 'LU', 'MK': 'MK', 'NO': 'NO', 'PL': 'PL', 'RO': 'RO',
            'RS': 'RS', 'SA': 'SA', 'SE': 'SE', 'SK': 'SK', 'UY': 'UY'
        }
        
        def extract_country(client_code):
            if pd.isna(client_code):
                return 'Unknown'
            prefix = str(client_code)[:2].upper()
            # Si numérique (00-99), c'est France
            if prefix.isdigit():
                return 'FR'
            return country_mapping.get(prefix, 'Unknown')
        
        df['Country'] = df['Cpt Client'].apply(extract_country)
        print(f"      ✅ Colonne Country créée depuis Cpt Client ({df['Country'].nunique()} pays)")
    
    # 5. Conversion des dates si nécessaire
    if 'Date Cde' in df.columns:
        df['Date Cde'] = pd.to_datetime(df['Date Cde'], errors='coerce')
        df = df.dropna(subset=['Date Cde'])
        
        # Ne garder que 2024 si présent
        if df['Date Cde'].dt.year.nunique() > 1:
            df = df[df['Date Cde'].dt.year == 2024].copy()
            print(f"      ✅ Filtré sur année 2024")
        
        # Recalculer Quarter depuis Date Cde
        df['Quarter'] = df['Date Cde'].dt.to_period('Q').astype(str)
    
    # Variables numériques clés
    variables_num = ['Montant', 'Quantité', 'PU Net']
    
    # Supprimer les valeurs nulles restantes
    df_clean = df.dropna(subset=[col for col in variables_num if col in df.columns]).copy()
    
    lignes_finales = len(df_clean)
    lignes_supprimees = lignes_initiales - lignes_finales
    
    print(f"      📊 Lignes après nettoyage : {lignes_finales:,}")
    print(f"      🗑️ Total supprimé : {lignes_supprimees:,} lignes ({lignes_supprimees/lignes_initiales*100:.2f}%)")
    
    # Rapport de nettoyage détaillé
    rapport_nettoyage = f"""
    <div class="alert alert-info">
        <h5><i class="bi bi-info-circle"></i> Rapport de Nettoyage des Données</h5>
        <p class="mb-2"><strong>📊 Lignes initiales : {lignes_initiales:,}</strong></p>
        <ul class="mb-2">
            <li>❌ Supprimé <strong>{qty_zero:,}</strong> lignes avec Quantité = 0</li>
            <li>❌ Supprimé <strong>{montant_zero:,}</strong> lignes avec Montant = 0</li>
            <li>❌ Supprimé <strong>{qty_negative:,}</strong> lignes avec Quantité négative</li>
            <li>❌ Supprimé <strong>{montant_negative:,}</strong> lignes avec Montant négatif</li>
        </ul>
        <p class="mb-2"><strong>📊 Lignes après nettoyage : {lignes_finales:,}</strong></p>
        <p class="mb-2"><strong>🗑️ Total supprimé : {lignes_supprimees:,} lignes ({lignes_supprimees/lignes_initiales*100:.2f}%)</strong></p>
        
        <hr>
        <p class="mb-1"><strong>Critères de nettoyage appliqués :</strong></p>
        <ul class="mb-0">
            <li>✅ Suppression des Quantités nulles ou négatives</li>
            <li>✅ Suppression des Montants nuls ou négatifs</li>
            <li>✅ Recalcul du PU Net (Montant / Quantité)</li>
            <li>✅ Extraction automatique du pays (Country) depuis Cpt Client</li>
            <li>✅ Conversion et validation des dates</li>
            <li>✅ Filtrage sur l'année 2024</li>
            <li>✅ Recalcul des Quarters depuis Date Cde</li>
        </ul>
    </div>
    """
    results['rapport_nettoyage'] = rapport_nettoyage
    
    # KPIs de base (sur données nettoyées)
    kpis['total_transactions'] = f"{len(df_clean):,}"
    kpis['total_lignes_clean'] = f"{len(df_clean):,}"
    kpis['ca_total'] = f"{df_clean['Montant'].sum():,.2f} €" if 'Montant' in df_clean.columns else "N/A"
    kpis['nb_clients'] = f"{df_clean['Cpt Client'].nunique():,}" if 'Cpt Client' in df_clean.columns else "N/A"
    kpis['nb_familles'] = f"{df_clean['Famille'].nunique():,}" if 'Famille' in df_clean.columns else "N/A"
    kpis['nb_pays'] = f"{df_clean['Country'].nunique():,}" if 'Country' in df_clean.columns else "N/A"
    kpis['panier_moyen'] = f"{df_clean['Montant'].mean():.2f} €" if 'Montant' in df_clean.columns else "N/A"
    kpis['quantite_moyenne'] = f"{df_clean['Quantité'].mean():.2f}" if 'Quantité' in df_clean.columns else "N/A"
    
    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 2 : ANALYSE STATISTIQUE COMPLÈTE DES VARIABLES
    # ═══════════════════════════════════════════════════════════════════
    
    print("   📊 Étape 2 : Analyse statistique complète...")
    
    # 2.1 STATISTIQUES DESCRIPTIVES COMPLÈTES
    stats_table = []
    for var in variables_num:
        if var in df_clean.columns:
            stats_table.append({
                'Variable': var,
                'Nombre': f"{df_clean[var].count():,}",
                'Moyenne': f"{df_clean[var].mean():.2f}",
                'Médiane': f"{df_clean[var].median():.2f}",
                'Écart-type': f"{df_clean[var].std():.2f}",
                'CV (%)': f"{(df_clean[var].std() / df_clean[var].mean() * 100):.2f}",
                'Asymétrie': f"{df_clean[var].skew():.2f}",
                'Aplatissement': f"{df_clean[var].kurtosis():.2f}",
                'Min': f"{df_clean[var].min():.2f}",
                'Q1': f"{df_clean[var].quantile(0.25):.2f}",
                'Q2': f"{df_clean[var].quantile(0.50):.2f}",
                'Q3': f"{df_clean[var].quantile(0.75):.2f}",
                'Max': f"{df_clean[var].max():.2f}"
            })
    
    results['stats_descriptives'] = pd.DataFrame(stats_table).to_html(
        classes='table table-striped table-hover table-sm',
        index=False,
        border=0
    )
    
    # 2.2 TESTS DE NORMALITÉ (Shapiro-Wilk)
    print("      • Tests de normalité...")
    normalite_tests = []
    for var in variables_num:
        if var in df.columns and len(df[var].dropna()) > 0:
            sample = df[var].dropna().sample(min(5000, len(df[var].dropna())))
            stat, p_value = scipy_stats.shapiro(sample)
            
            normalite_tests.append({
                'Variable': var,
                'Statistique W': f"{stat:.4f}",
                'p-value': f"{p_value:.4e}",
                'Résultat': 'Non normale ❌' if p_value < 0.05 else 'Normale ✅',
                'Interprétation': 'La distribution est significativement différente de la normale' if p_value < 0.05 
                                 else 'La distribution suit approximativement une loi normale'
            })
    
    results['tests_normalite'] = pd.DataFrame(normalite_tests).to_html(
        classes='table table-striped table-hover',
        index=False,
        border=0,
        escape=False
    )
    
    # 2.3 DÉTECTION DES VALEURS ABERRANTES (Méthode IQR)
    print("      • Détection des outliers...")
    outliers_info = []
    for var in variables_num:
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
                'Q1': f"{Q1:.2f}",
                'Q3': f"{Q3:.2f}",
                'IQR': f"{IQR:.2f}",
                'Borne Inf': f"{lower_bound:.2f}",
                'Borne Sup': f"{upper_bound:.2f}",
                'Nombre Outliers': f"{len(outliers):,}",
                'Pourcentage': f"{pct:.2f}%",
                'Impact': '🔴 Élevé' if pct > 10 else '🟡 Modéré' if pct > 5 else '🟢 Faible'
            })
    
    results['valeurs_aberrantes'] = pd.DataFrame(outliers_info).to_html(
        classes='table table-striped table-hover',
        index=False,
        border=0,
        escape=False
    )
    
    # 2.4 MATRICE DE CORRÉLATION
    print("      • Matrice de corrélation...")
    if all(col in df.columns for col in variables_num):
        corr = df[variables_num].corr()
        
        # Analyse des corrélations
        corr_analysis = []
        for i in range(len(variables_num)):
            for j in range(i+1, len(variables_num)):
                var1, var2 = variables_num[i], variables_num[j]
                corr_val = corr.loc[var1, var2]
                
                if abs(corr_val) > 0.7:
                    force = "Très forte"
                elif abs(corr_val) > 0.5:
                    force = "Forte"
                elif abs(corr_val) > 0.3:
                    force = "Modérée"
                else:
                    force = "Faible"
                
                signe = "positive" if corr_val > 0 else "négative"
                
                corr_analysis.append({
                    'Variable 1': var1,
                    'Variable 2': var2,
                    'Corrélation': f"{corr_val:.3f}",
                    'Force': force,
                    'Signe': signe,
                    'Interprétation': f"Corrélation {force.lower()} {signe} entre {var1} et {var2}"
                })
        
        results['correlation_analysis'] = pd.DataFrame(corr_analysis).to_html(
            classes='table table-striped table-hover',
            index=False,
            border=0
        )
        
        # Graphique matrice de corrélation
        fig = go.Figure(data=go.Heatmap(
            z=corr.values,
            x=corr.columns,
            y=corr.columns,
            text=np.round(corr.values, 3),
            texttemplate='<b>%{text}</b>',
            textfont={"size": 14, "color": "white"},
            colorscale='RdBu_r',
            zmid=0,
            zmin=-1,
            zmax=1,
            colorbar=dict(title="Corrélation", thickness=15)
        ))
        
        fig.update_layout(
            title='<b>📊 MATRICE DE CORRÉLATION (Pearson)</b>',
            height=500,
            template='plotly_white',
            xaxis_title='',
            yaxis_title='',
            font=dict(size=12)
        )
        graphs['correlation_matrix'] = fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 3 : VISUALISATIONS STATISTIQUES COMPLÈTES
    # ═══════════════════════════════════════════════════════════════════
    
    print("   📈 Étape 3 : Génération des visualisations...")
    
    # 3.1 ANALYSE COMPLÈTE DU MONTANT
    print("      • Distribution du Montant (histogramme + boxplot + Q-Q plot)...")
    if 'Montant' in df.columns:
        fig = make_subplots(
            rows=3, cols=1,
            row_heights=[0.5, 0.2, 0.3],
            subplot_titles=(
                '📊 Distribution du Montant',
                '📦 Boxplot - Détection des Outliers',
                '📐 Q-Q Plot - Test de Normalité'
            ),
            vertical_spacing=0.12
        )
        
        # Histogramme
        fig.add_trace(
            go.Histogram(
                x=df['Montant'],
                nbinsx=50,
                name='Montant',
                marker_color='steelblue',
                showlegend=False
            ),
            row=1, col=1
        )
        
        # Ajout lignes moyenne et médiane
        mean_val = df['Montant'].mean()
        median_val = df['Montant'].median()
        
        fig.add_vline(x=mean_val, line_dash="dash", line_color="red", 
                     annotation_text=f"Moyenne: {mean_val:.0f}", row=1, col=1)
        fig.add_vline(x=median_val, line_dash="dash", line_color="green",
                     annotation_text=f"Médiane: {median_val:.0f}", row=1, col=1)
        
        # Boxplot
        fig.add_trace(
            go.Box(
                x=df['Montant'],
                name='Montant',
                marker_color='indianred',
                showlegend=False
            ),
            row=2, col=1
        )
        
        # Q-Q Plot
        sample_data = df['Montant'].dropna().sample(min(5000, len(df['Montant'].dropna())))
        theoretical_quantiles = scipy_stats.norm.ppf(np.linspace(0.01, 0.99, len(sample_data)))
        observed_quantiles = np.sort(sample_data.values)
        
        fig.add_trace(
            go.Scatter(
                x=theoretical_quantiles,
                y=observed_quantiles,
                mode='markers',
                marker=dict(color='blue', size=4),
                name='Données observées',
                showlegend=False
            ),
            row=3, col=1
        )
        
        # Ligne théorique
        fig.add_trace(
            go.Scatter(
                x=theoretical_quantiles,
                y=np.polyval(np.polyfit(theoretical_quantiles, observed_quantiles, 1), theoretical_quantiles),
                mode='lines',
                line=dict(color='red', dash='dash'),
                name='Distribution normale',
                showlegend=False
            ),
            row=3, col=1
        )
        
        fig.update_xaxes(title_text="Montant (€)", row=1, col=1)
        fig.update_yaxes(title_text="Fréquence", row=1, col=1)
        fig.update_xaxes(title_text="Montant (€)", row=2, col=1)
        fig.update_xaxes(title_text="Quantiles Théoriques", row=3, col=1)
        fig.update_yaxes(title_text="Quantiles Observés", row=3, col=1)
        
        fig.update_layout(
            height=900,
            title_text="<b>📊 ANALYSE STATISTIQUE COMPLÈTE DES VARIABLES - Montant</b>",
            template='plotly_white',
            showlegend=False
        )
        
        graphs['dist_complete_montant'] = fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    # 3.2 ANALYSE COMPLÈTE DE LA QUANTITÉ
    print("      • Distribution de la Quantité...")
    if 'Quantité' in df.columns:
        fig = make_subplots(
            rows=3, cols=1,
            row_heights=[0.5, 0.2, 0.3],
            subplot_titles=(
                '📊 Distribution de la Quantité',
                '📦 Boxplot',
                '📐 Q-Q Plot'
            ),
            vertical_spacing=0.12
        )
        
        fig.add_trace(go.Histogram(x=df['Quantité'], nbinsx=50, marker_color='mediumseagreen'), row=1, col=1)
        fig.add_trace(go.Box(x=df['Quantité'], marker_color='orange'), row=2, col=1)
        
        # Q-Q Plot
        sample_data = df['Quantité'].dropna().sample(min(5000, len(df['Quantité'].dropna())))
        theoretical_quantiles = scipy_stats.norm.ppf(np.linspace(0.01, 0.99, len(sample_data)))
        observed_quantiles = np.sort(sample_data.values)
        
        fig.add_trace(go.Scatter(x=theoretical_quantiles, y=observed_quantiles, mode='markers',
                                marker=dict(color='green', size=4)), row=3, col=1)
        fig.add_trace(go.Scatter(x=theoretical_quantiles,
                                y=np.polyval(np.polyfit(theoretical_quantiles, observed_quantiles, 1), theoretical_quantiles),
                                mode='lines', line=dict(color='red', dash='dash')), row=3, col=1)
        
        fig.update_layout(height=900, title_text="<b>📊 ANALYSE STATISTIQUE COMPLÈTE - Quantité</b>",
                         template='plotly_white', showlegend=False)
        
        graphs['dist_complete_quantite'] = fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    # 3.3 ANALYSE COMPLÈTE DU PU NET
    print("      • Distribution du PU Net...")
    if 'PU Net' in df.columns:
        fig = make_subplots(
            rows=3, cols=1,
            row_heights=[0.5, 0.2, 0.3],
            subplot_titles=(
                '📊 Distribution du PU Net',
                '📦 Boxplot',
                '📐 Q-Q Plot'
            ),
            vertical_spacing=0.12
        )
        
        fig.add_trace(go.Histogram(x=df['PU Net'], nbinsx=50, marker_color='purple'), row=1, col=1)
        fig.add_trace(go.Box(x=df['PU Net'], marker_color='darkorange'), row=2, col=1)
        
        # Q-Q Plot
        sample_data = df['PU Net'].dropna().sample(min(5000, len(df['PU Net'].dropna())))
        theoretical_quantiles = scipy_stats.norm.ppf(np.linspace(0.01, 0.99, len(sample_data)))
        observed_quantiles = np.sort(sample_data.values)
        
        fig.add_trace(go.Scatter(x=theoretical_quantiles, y=observed_quantiles, mode='markers',
                                marker=dict(color='purple', size=4)), row=3, col=1)
        fig.add_trace(go.Scatter(x=theoretical_quantiles,
                                y=np.polyval(np.polyfit(theoretical_quantiles, observed_quantiles, 1), theoretical_quantiles),
                                mode='lines', line=dict(color='red', dash='dash')), row=3, col=1)
        
        fig.update_layout(height=900, title_text="<b>📊 ANALYSE STATISTIQUE COMPLÈTE - PU Net</b>",
                         template='plotly_white', showlegend=False)
        
        graphs['dist_complete_pu_net'] = fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    # 3.4 TOP 10 PAYS PAR CA (si colonne Country existe)
    print("      • Top 10 Pays par CA...")
    if 'Country' in df.columns and 'Montant' in df.columns:
        ca_par_pays = df.groupby('Country')['Montant'].sum().sort_values(ascending=False).head(10)
        
        fig = go.Figure(data=[
            go.Bar(
                x=ca_par_pays.index,
                y=ca_par_pays.values,
                marker_color='indianred',
                text=[f"{v:,.0f}€" for v in ca_par_pays.values],
                textposition='outside',
                textfont=dict(size=11, color='black', family='Arial Black')
            )
        ])
        fig.update_layout(
            title='<b>🌍 Top 10 Pays par Chiffre d\'Affaires</b>',
            xaxis_title='Pays',
            yaxis_title='CA (€)',
            height=500,
            template='plotly_white',
            font=dict(size=12)
        )
        graphs['top_pays'] = fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    # 3.5 TOP 10 FAMILLES DE PRODUITS
    print("      • Top 10 Familles de produits...")
    if 'Famille' in df.columns and 'Montant' in df.columns:
        ca_par_famille = df.groupby('Famille')['Montant'].sum().sort_values(ascending=False).head(10)
        
        fig = go.Figure(data=[
            go.Bar(
                x=ca_par_famille.values,
                y=ca_par_famille.index,
                orientation='h',
                marker_color='steelblue',
                text=[f"{v:,.0f}€" for v in ca_par_famille.values],
                textposition='outside',
                textfont=dict(size=10, color='black', family='Arial Black')
            )
        ])
        fig.update_layout(
            title='<b>📦 Top 10 Familles de Produits par CA</b>',
            xaxis_title='CA (€)',
            yaxis_title='Famille',
            height=600,
            template='plotly_white',
            font=dict(size=11)
        )
        graphs['top_familles'] = fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    # 3.6 ÉVOLUTION TRIMESTRIELLE
    print("      • Évolution trimestrielle...")
    if 'Quarter' in df.columns and 'Montant' in df.columns:
        ca_par_quarter = df.groupby('Quarter')['Montant'].sum()
        
        fig = go.Figure(data=[
            go.Scatter(
                x=ca_par_quarter.index,
                y=ca_par_quarter.values,
                mode='lines+markers',
                marker=dict(size=15, color='steelblue', line=dict(width=2, color='white')),
                line=dict(width=4, color='steelblue'),
                text=[f"{v:,.0f}€" for v in ca_par_quarter.values],
                textposition='top center',
                textfont=dict(size=12, color='black', family='Arial Black')
            )
        ])
        fig.update_layout(
            title='<b>📅 Évolution du CA par Trimestre 2024</b>',
            xaxis_title='Trimestre',
            yaxis_title='CA (€)',
            height=500,
            template='plotly_white',
            font=dict(size=12)
        )
        graphs['evolution_quarter'] = fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    # ═══════════════════════════════════════════════════════════════════
    # SYNTHÈSE DE L'ANALYSE STATISTIQUE
    # ═══════════════════════════════════════════════════════════════════
    
    print("   📝 Génération de la synthèse...")
    
    synthese = f"""
    <div class="card border-info">
        <div class="card-header bg-info text-white">
            <h5 class="mb-0">📝 SYNTHÈSE DE L'ANALYSE STATISTIQUE</h5>
        </div>
        <div class="card-body">
            <h6 class="text-primary">🔍 Principaux constats :</h6>
            <ul>
                <li><strong>Volume de données :</strong> {kpis['total_transactions']} transactions analysées</li>
                <li><strong>Chiffre d'affaires total :</strong> {kpis['ca_total']}</li>
                <li><strong>Panier moyen :</strong> {kpis['panier_moyen']}</li>
                <li><strong>Nombre de clients :</strong> {kpis['nb_clients']}</li>
                <li><strong>Nombre de familles de produits :</strong> {kpis['nb_familles']}</li>
                <li><strong>Couverture géographique :</strong> {kpis['nb_pays']} pays</li>
            </ul>
            
            <h6 class="text-primary mt-3">📊 Observations sur les distributions :</h6>
            <ul>
                <li><strong>Normalité :</strong> Les variables ne suivent pas une distribution normale (tests de Shapiro-Wilk significatifs)</li>
                <li><strong>Asymétrie :</strong> Distributions fortement asymétriques à droite (présence de gros clients/commandes)</li>
                <li><strong>Outliers :</strong> Présence significative de valeurs aberrantes à traiter selon le contexte métier</li>
            </ul>
            
            <h6 class="text-primary mt-3">🔗 Corrélations identifiées :</h6>
            <ul>
                <li><strong>Montant vs Quantité :</strong> Corrélation forte positive (logique : plus de quantité = plus de CA)</li>
                <li><strong>Montant vs PU Net :</strong> Corrélation faible (effet prix/volume variable)</li>
            </ul>
            
            <h6 class="text-primary mt-3">💡 Recommandations :</h6>
            <ul>
                <li>Utiliser des méthodes non-paramétriques pour les tests statistiques</li>
                <li>Segmenter l'analyse par pays et famille de produits</li>
                <li>Analyser séparément les gros clients (outliers) vs clients réguliers</li>
                <li>Explorer les variations temporelles (saisonnalité, tendances)</li>
            </ul>
        </div>
    </div>
    """
    
    results['synthese_analyse'] = synthese
    
    print("✅ Analyse statistique complète générée !")
    
    return {
        'results': results,
        'graphs': graphs,
        'kpis': kpis
    }
