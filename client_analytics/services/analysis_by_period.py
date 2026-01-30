"""
Service pour le sous-onglet ANALYSE PAR PÉRIODES
Génère les statistiques complètes pour une période donnée (mois, trimestre, année fiscale)
AUTONOME - Ne dépend d'aucun autre fichier de services
"""
import pandas as pd
import numpy as np
from scipy import stats
from .visualizations import viz_by_period


def analyze_correlations_detailed(df, variables):
    """
    Génère une analyse détaillée des corrélations avec interprétations business
    
    Args:
        df: DataFrame
        variables: Liste des variables numériques
    
    Returns:
        HTML avec l'analyse des corrélations
    """
    try:
        corr_matrix = df[variables].corr()
        
        html = "<div class='correlation-analysis'>"
        html += "<h6><strong>📊 Corrélations Significatives Détectées :</strong></h6>"
        html += "<ul>"
        
        # Analyser les paires de corrélations
        for i, var1 in enumerate(variables):
            for j, var2 in enumerate(variables):
                if i < j:  # Éviter les doublons et la diagonale
                    corr_value = corr_matrix.loc[var1, var2]
                    
                    # Ne garder que les corrélations significatives (|r| > 0.3)
                    if abs(corr_value) > 0.3:
                        strength = ""
                        interpretation = ""
                        
                        if abs(corr_value) > 0.7:
                            strength = "forte"
                            color = "danger"
                        elif abs(corr_value) > 0.5:
                            strength = "modérée"
                            color = "warning"
                        else:
                            strength = "faible à modérée"
                            color = "info"
                        
                        direction = "positive" if corr_value > 0 else "négative"
                        
                        # Interprétations business spécifiques
                        if var1 == "Montant" and var2 == "Quantité":
                            if corr_value > 0.5:
                                interpretation = "Les commandes avec plus d'unités génèrent des montants plus élevés, suggérant une stratégie de volume efficace."
                            else:
                                interpretation = "Corrélation faible : certains produits à forte valeur unitaire génèrent du CA même avec peu d'unités."
                        elif var1 == "Montant" and var2 == "PU Net":
                            if corr_value > 0.5:
                                interpretation = "Les produits à prix élevé contribuent significativement au CA, suggérant une clientèle premium."
                            else:
                                interpretation = "Le CA n'est pas uniquement dû aux prix élevés, le volume joue aussi un rôle important."
                        elif var1 == "Quantité" and var2 == "PU Net":
                            if corr_value < -0.3:
                                interpretation = "Les produits à bas prix sont achetés en plus grande quantité (stratégie volume)."
                            else:
                                interpretation = "Pas de relation claire entre prix et quantité commandée."
                        
                        html += f"<li><span class='badge bg-{color}'>{var1} ↔ {var2}</span>: "
                        html += f"Corrélation <strong>{direction} {strength}</strong> (r = {corr_value:.3f})<br>"
                        if interpretation:
                            html += f"<em class='text-muted'>→ {interpretation}</em>"
                        html += "</li>"
        
        html += "</ul>"
        
        # Recommandations basées sur les corrélations
        html += "<h6 class='mt-3'><strong>💡 Recommandations :</strong></h6>"
        html += "<ul class='text-muted'>"
        
        montant_quantite = corr_matrix.loc['Montant', 'Quantité'] if 'Montant' in corr_matrix.index and 'Quantité' in corr_matrix.columns else 0
        montant_pu = corr_matrix.loc['Montant', 'PU Net'] if 'Montant' in corr_matrix.index and 'PU Net' in corr_matrix.columns else 0
        
        if montant_quantite > 0.6:
            html += "<li>🎯 Stratégie volume : Encouragez les achats en grande quantité avec des remises progressives.</li>"
        
        if montant_pu > 0.6:
            html += "<li>💎 Clientèle premium : Développez votre gamme de produits haut de gamme.</li>"
        
        if abs(montant_quantite - montant_pu) < 0.2:
            html += "<li>⚖️ Mix équilibré : Votre CA est équilibré entre volume et valeur unitaire, maintenez cette diversification.</li>"
        
        html += "</ul>"
        html += "</div>"
        
        return html
    except Exception as e:
        print(f"   ⚠️ Erreur analyse corrélations: {e}")
        return "<p class='text-danger'>Erreur lors de l'analyse des corrélations</p>"


def generate_deep_synthesis(df, kpis, variables_num):
    """
    Génère une synthèse approfondie de l'analyse mensuelle
    
    Args:
        df: DataFrame nettoyé
        kpis: Dictionnaire des KPIs
        variables_num: Liste des variables numériques
    
    Returns:
        HTML avec la synthèse détaillée
    """
    try:
        html = "<div class='synthesis'>"
        
        # 1. Vue d'ensemble
        html += "<h6><strong>📈 Vue d'Ensemble de la Performance</strong></h6>"
        html += "<div class='alert alert-light border'>"
        html += f"<p>Sur la période analysée, nous observons <strong>{kpis.get('total_transactions', 'N/A')} transactions</strong> "
        html += f"générées par <strong>{kpis.get('nb_clients', 'N/A')} clients</strong> distincts, "
        html += f"pour un chiffre d'affaires total de <strong>{kpis.get('ca_total', 'N/A')}</strong>.</p>"
        
        panier_moyen = df['Montant'].mean() if 'Montant' in df.columns else 0
        html += f"<p>Le panier moyen s'établit à <strong>{panier_moyen:,.2f} €</strong>. "
        
        # Analyser la distribution du panier moyen
        if 'Montant' in df.columns:
            median = df['Montant'].median()
            if panier_moyen > median * 1.2:
                html += "La moyenne est significativement supérieure à la médiane, indiquant la présence de quelques commandes de très haute valeur qui tirent la moyenne vers le haut.</p>"
            else:
                html += "La moyenne est proche de la médiane, suggérant une distribution relativement homogène des montants.</p>"
        
        html += "</div>"
        
        # 2. Qualité des données et normalité
        html += "<h6 class='mt-4'><strong>📊 Caractéristiques Statistiques des Données</strong></h6>"
        html += "<div class='alert alert-info border'>"
        
        # Tests de normalité
        normality_results = {}
        for var in variables_num:
            if var in df.columns:
                data = df[var].dropna()
                if len(data) > 3:
                    stat, p_value = stats.shapiro(data[:5000])  # Limite à 5000 échantillons
                    normality_results[var] = p_value
        
        html += "<p><strong>Distribution des données :</strong></p>"
        html += "<ul>"
        non_normal = [var for var, p in normality_results.items() if p < 0.05]
        if len(non_normal) == len(normality_results):
            html += "<li>✓ Toutes les variables présentent une distribution <strong>non normale</strong> (test de Shapiro-Wilk, p < 0.05). "
            html += "Ceci est attendu dans les données commerciales qui présentent souvent des distributions asymétriques avec des valeurs extrêmes.</li>"
        else:
            html += f"<li>✓ {len(non_normal)}/{len(normality_results)} variables ont une distribution non normale.</li>"
        html += "</ul>"
        
        # Valeurs aberrantes
        html += "<p><strong>Valeurs aberrantes :</strong></p>"
        html += "<ul>"
        for var in variables_num:
            if var in df.columns:
                Q1 = df[var].quantile(0.25)
                Q3 = df[var].quantile(0.75)
                IQR = Q3 - Q1
                outliers = df[(df[var] < Q1 - 1.5*IQR) | (df[var] > Q3 + 1.5*IQR)]
                pct_outliers = (len(outliers) / len(df)) * 100
                
                html += f"<li><strong>{var}</strong> : {len(outliers):,} outliers détectés "
                html += f"({pct_outliers:.1f}% des données)"
                
                if pct_outliers > 10:
                    html += " - <span class='text-warning'>⚠️ Proportion élevée, nécessite une attention particulière</span>"
                elif pct_outliers > 5:
                    html += " - <span class='text-info'>ℹ️ Proportion modérée, à surveiller</span>"
                else:
                    html += " - <span class='text-success'>✓ Proportion normale</span>"
                
                html += "</li>"
        html += "</ul>"
        html += "</div>"
        
        # 3. Insights business
        html += "<h6 class='mt-4'><strong>💼 Insights Business</strong></h6>"
        html += "<div class='alert alert-success border'>"
        html += "<ul>"
        
        # Analyser la variabilité
        if 'Montant' in df.columns:
            cv = (df['Montant'].std() / df['Montant'].mean()) * 100
            html += f"<li><strong>Variabilité des montants</strong> : Coefficient de variation = {cv:.1f}%. "
            if cv > 100:
                html += "Très forte dispersion des montants, indiquant une grande diversité dans les types de transactions.</li>"
            elif cv > 50:
                html += "Dispersion modérée, typique d'un portefeuille client diversifié.</li>"
            else:
                html += "Faible dispersion, les transactions sont relativement homogènes.</li>"
        
        # Concentration du CA
        if 'Cpt Client' in df.columns and 'Montant' in df.columns:
            ca_by_client = df.groupby('Cpt Client')['Montant'].sum().sort_values(ascending=False)
            top_20_pct_ca = (ca_by_client.head(int(len(ca_by_client)*0.2)).sum() / ca_by_client.sum()) * 100
            html += f"<li><strong>Concentration client</strong> : Les 20% de clients les plus importants représentent {top_20_pct_ca:.1f}% du CA. "
            
            if top_20_pct_ca > 80:
                html += "<span class='text-danger'>⚠️ Forte concentration (principe de Pareto dépassé), risque de dépendance élevé.</span></li>"
            elif top_20_pct_ca > 60:
                html += "<span class='text-warning'>Concentration modérée, conforme au principe de Pareto.</span></li>"
            else:
                html += "<span class='text-success'>CA bien réparti entre les clients.</span></li>"
        
        # Analyse géographique si disponible
        if 'Country' in df.columns and 'Montant' in df.columns:
            ca_by_country = df.groupby('Country')['Montant'].sum().sort_values(ascending=False)
            top_country_pct = (ca_by_country.iloc[0] / ca_by_country.sum()) * 100
            html += f"<li><strong>Concentration géographique</strong> : Le pays principal représente {top_country_pct:.1f}% du CA. "
            
            if top_country_pct > 50:
                html += "⚠️ Forte dépendance à un seul marché, considérez la diversification géographique.</li>"
            else:
                html += "✓ Bonne diversification géographique.</li>"
        
        html += "</ul>"
        html += "</div>"
        
        # 4. Recommandations stratégiques
        html += "<h6 class='mt-4'><strong>🎯 Recommandations Stratégiques</strong></h6>"
        html += "<div class='alert alert-warning border'>"
        html += "<ol>"
        html += "<li><strong>Gestion des outliers</strong> : Identifiez manuellement les transactions exceptionnelles (très élevées ou très basses) pour comprendre leur origine et les reproduire ou les éviter.</li>"
        html += "<li><strong>Segmentation client</strong> : Utilisez l'analyse de clustering pour identifier des segments de clients homogènes et adapter votre stratégie commerciale.</li>"
        html += "<li><strong>Prévisions</strong> : En raison de la distribution non normale, privilégiez les méthodes de prévision robustes (médiane, quantiles) plutôt que les moyennes.</li>"
        
        if 'Month' in df.columns:
            html += "<li><strong>Analyse de saisonnalité</strong> : Examinez l'évolution mensuelle pour détecter des patterns saisonniers et optimiser vos stocks et campagnes marketing.</li>"
        
        html += "<li><strong>Optimisation du mix produit</strong> : Basé sur les corrélations, ajustez votre stratégie entre produits à fort volume/faible marge et produits premium/faible volume.</li>"
        html += "</ol>"
        html += "</div>"
        
        # 5. Points d'attention
        html += "<h6 class='mt-4'><strong>⚠️ Points d'Attention</strong></h6>"
        html += "<div class='alert alert-danger border'>"
        html += "<ul>"
        
        # Vérifier les valeurs nulles
        null_counts = df[variables_num].isnull().sum()
        if null_counts.sum() > 0:
            html += "<li><strong>Données manquantes</strong> : "
            for var, count in null_counts[null_counts > 0].items():
                pct = (count / len(df)) * 100
                html += f"{var} : {count} valeurs manquantes ({pct:.1f}%). "
            html += "</li>"
        
        # Vérifier les valeurs négatives
        for var in variables_num:
            if var in df.columns:
                neg_count = (df[var] < 0).sum()
                if neg_count > 0:
                    html += f"<li><strong>Valeurs négatives dans {var}</strong> : {neg_count} valeurs négatives détectées. Vérifiez s'il s'agit d'avoirs ou d'erreurs de saisie.</li>"
        
        html += "<li><strong>Qualité des analyses</strong> : Les distributions non normales impliquent que certains tests statistiques classiques (t-test, ANOVA) ne sont pas appropriés. Privilégiez les tests non-paramétriques (Mann-Whitney, Kruskal-Wallis).</li>"
        html += "</ul>"
        html += "</div>"
        
        html += "</div>"
        
        return html
    except Exception as e:
        print(f"   ⚠️ Erreur génération synthèse: {e}")
        import traceback
        traceback.print_exc()
        return "<p class='text-danger'>Erreur lors de la génération de la synthèse</p>"


def generate_period_analysis(df, granularity='month', skip_preprocessing=True):
    """
    Génère l'analyse statistique pour une période spécifique
    
    Args:
        df: DataFrame filtré pour la période
        granularity: 'month', 'quarter', 'year' - détermine l'agrégation temporelle
        skip_preprocessing: Si True, ne fait PAS de nettoyage supplémentaire
                           (les données sont déjà filtrées et nettoyées)
    
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
    
    print(f"📊 Génération de l'analyse par période (granularité: {granularity})...")
    if skip_preprocessing:
        print("   ⚠️ Mode skip_preprocessing=True : conservation des données exactes")
    
    # Mapping des colonnes temporelles selon la granularité
    time_columns = {
        'month': 'Month',
        'quarter': 'Quarter',
        'year': 'Fiscal_Year_Label'
    }
    time_col = time_columns.get(granularity, 'Month')
    
    lignes_initiales = len(df)
    variables_num = ['Montant', 'Quantité', 'PU Net']
    
    # Utiliser les données telles quelles en mode skip
    df_clean = df.copy()
    lignes_finales = len(df_clean)
    
    # KPIs de base
    kpis['total_transactions'] = f"{len(df_clean):,}"
    kpis['ca_total'] = f"{df_clean['Montant'].sum():,.2f} €" if 'Montant' in df_clean.columns else "N/A"
    kpis['nb_clients'] = f"{df_clean['Cpt Client'].nunique():,}" if 'Cpt Client' in df_clean.columns else "N/A"
    kpis['panier_moyen'] = f"{df_clean['Montant'].mean():.2f} €" if 'Montant' in df_clean.columns else "N/A"
    
    # KPI Familles / Pays (robuste aux noms de colonnes)
    def _pick_col(df, candidates):
        for c in candidates:
            if c in df.columns:
                return c
        return None
    
    fam_col = _pick_col(df_clean, ["FAMILLE", "Famille", "famille", "Famille 1"])
    country_col = _pick_col(df_clean, ["COUNTRY", "Country", "PAYS", "Pays", "country"])
    
    families_count = int(df_clean[fam_col].nunique(dropna=True)) if fam_col else 0
    countries_count = int(df_clean[country_col].nunique(dropna=True)) if country_col else 0
    
    kpis['nb_familles'] = f"{families_count:,}"
    kpis['nb_pays'] = f"{countries_count:,}"
    
    # Statistiques descriptives
    stats_table = []
    for var in variables_num:
        if var in df_clean.columns:
            stats_table.append({
                'Variable': var,
                'Moyenne': f"{df_clean[var].mean():.2f}",
                'Médiane': f"{df_clean[var].median():.2f}",
                'Écart-type': f"{df_clean[var].std():.2f}",
                'Min': f"{df_clean[var].min():.2f}",
                'Max': f"{df_clean[var].max():.2f}"
            })
    
    results['stats_descriptives'] = pd.DataFrame(stats_table).to_html(
        classes='table table-striped',
        index=False
    )
    
    # ═══════════════════════════════════════════════════════════════════
    # GÉNÉRATION DES GRAPHIQUES
    # ═══════════════════════════════════════════════════════════════════
    print("📊 Génération des graphiques...")
    
    # 1. Matrice de corrélation
    if all(col in df_clean.columns for col in variables_num):
        graphs['correlation_matrix'] = viz_by_period.create_correlation_matrix(df_clean, variables_num)
        # Analyse détaillée des corrélations
        results['correlation_analysis'] = analyze_correlations_detailed(df_clean, variables_num)
    
    # 2. Tests de normalité avec visualisations
    print("   → Génération des graphiques de test de normalité...")
    for var in variables_num:
        if var in df_clean.columns:
            # QQ-Plot
            qq_key = f'qq_plot_{var.lower().replace(" ", "_")}'
            graphs[qq_key] = viz_by_period.create_qq_plot(df_clean, var)
            
            # Histogramme avec courbe normale
            norm_key = f'normality_test_{var.lower().replace(" ", "_")}'
            graphs[norm_key] = viz_by_period.create_normality_test_plot(df_clean, var)
    
    # 3. Boxplot pour les valeurs aberrantes
    if all(col in df_clean.columns for col in variables_num):
        print("   → Génération du boxplot des valeurs aberrantes...")
        graphs['outliers_boxplot'] = viz_by_period.create_outliers_boxplot(df_clean, variables_num)
    
    # 4. Distributions des variables
    for var in ['Montant', 'Quantité', 'PU Net']:
        if var in df_clean.columns:
            graph_key = f'dist_complete_{var.lower().replace(" ", "_")}'
            graphs[graph_key] = viz_by_period.create_distribution_plot(df_clean, var)
    
    # 5. Top pays
    if 'Country' in df_clean.columns and 'Montant' in df_clean.columns:
        graphs['top_pays'] = viz_by_period.create_top_categories_plot(
            df_clean, 'Country', 'Montant', n_top=10, title='Top 10 Pays par CA'
        )
    
    # 6. Top familles
    if 'Famille' in df_clean.columns and 'Montant' in df_clean.columns:
        graphs['top_familles'] = viz_by_period.create_top_categories_plot(
            df_clean, 'Famille', 'Montant', n_top=10, title='Top 10 Familles par CA'
        )
    
    # 5. Agrégation temporelle selon la granularité choisie
    if time_col in df_clean.columns and 'Montant' in df_clean.columns:
        # Graphique en barres
        graphs['ca_par_trimestre'] = viz_by_period.create_temporal_aggregation_plot(
            df_clean, time_col, 'Montant', granularity
        )
        
        # Graphique d'évolution (ligne)
        graphs['evolution_mensuelle'] = viz_by_period.create_temporal_evolution_plot(
            df_clean, time_col, 'Montant', granularity
        )
        
        # Graphique de variation
        graphs['variation_trimestrielle'] = viz_by_period.create_variation_plot(
            df_clean, time_col, 'Montant', granularity
        )
    
    # ═══════════════════════════════════════════════════════════════════
    # SYNTHÈSE APPROFONDIE
    # ═══════════════════════════════════════════════════════════════════
    print("📝 Génération de la synthèse approfondie...")
    results['synthese_analyse'] = generate_deep_synthesis(df_clean, kpis, variables_num)
    
    print(f"✅ {len(graphs)} graphiques générés")
    
    print("✅ Analyse par période générée !")
    
    return {
        'results': results,
        'graphs': graphs,
        'kpis': kpis
    }
