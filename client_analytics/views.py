from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from .models import Dataset
from .forms import UploadDatasetForm, SelectDatasetForm
from .services import dataset_io, data_processing, analysis_currency_dependency
from .services import analysis_overview, analysis_by_period, analysis_time_series, analysis_clustering
from .services import analysis_products, analysis_geographic
import pandas as pd


def home(request):
    """Home page with upload and selection forms"""
    upload_form = UploadDatasetForm()
    select_form = SelectDatasetForm()
    
    if request.method == 'POST':
        if 'upload' in request.POST:
            upload_form = UploadDatasetForm(request.POST, request.FILES)
            if upload_form.is_valid():
                dataset = upload_form.save()
                messages.success(request, f'Dataset "{dataset.name}" uploadé avec succès!')
                return redirect('client_analytics:dataset_overview', pk=dataset.pk)
        
        elif 'select' in request.POST:
            select_form = SelectDatasetForm(request.POST)
            if select_form.is_valid():
                dataset = select_form.cleaned_data['existing_dataset']
                return redirect('client_analytics:dataset_overview', pk=dataset.pk)
    
    context = {
        'upload_form': upload_form,
        'select_form': select_form,
    }
    return render(request, 'client_analytics/home.html', context)


def workflow(request):
    """Workflow explanation page"""
    return render(request, 'client_analytics/workflow.html')


def dataset_overview(request, pk):
    """Dataset overview page"""
    dataset = get_object_or_404(Dataset, pk=pk)
    
    # Load dataframe (already processed during upload in forms.py)
    df = dataset_io.load_dataset_df(dataset)
    
    if df is None:
        messages.error(request, 'Erreur lors du chargement du dataset')
        return redirect('client_analytics:home')
    
    # Get dataset info using analysis_overview
    overview_analysis = analysis_overview.generate_overview_analysis(df)
    info = overview_analysis.get('info', {})
    missing_info = overview_analysis.get('missing_info', [])
    numeric_summary = overview_analysis.get('numeric_summary')
    column_types = overview_analysis.get('column_types', {})
    
    # Convert dataframe head to HTML
    df_head_html = df.head(10).to_html(classes='table table-striped table-sm', index=False)
    
    # Convert numeric summary to HTML
    numeric_summary_html = None
    if numeric_summary is not None:
        numeric_summary_html = numeric_summary.to_html(classes='table table-striped table-sm')
    
    context = {
        'dataset': dataset,
        'info': info,
        'missing_info': missing_info,
        'df_head_html': df_head_html,
        'numeric_summary_html': numeric_summary_html,
        'column_types': column_types,
    }
    return render(request, 'client_analytics/dataset_overview.html', context)


def stats(request, pk):
    """Statistics page - High Tech 2024 Analytics COMPLET + Nouvelles Analyses Temporelles"""
    dataset = get_object_or_404(Dataset, pk=pk)
    
    # ═══════════════════════════════════════════════════════════════════
    # 📊 CHARGEMENT DES DONNÉES DÉJÀ TRAITÉES
    # ═══════════════════════════════════════════════════════════════════
    # ⚠️ IMPORTANT : Les données ont été traitées UNE SEULE FOIS dans forms.py
    # lors de l'upload. On charge ici les données DÉJÀ NETTOYÉES.
    # NE PAS RAPPELER process_raw_data() !
    # ═══════════════════════════════════════════════════════════════════
    
    df_processed = dataset_io.load_dataset_df(dataset)
    
    if df_processed is None:
        messages.error(request, 'Erreur lors du chargement du dataset')
        return redirect('client_analytics:home')
    
    # ════════════════════════════════════════════════════════════════
    # PARTIE 1 : ANALYSES SUR DONNÉES DÉJÀ TRAITÉES
    # ════════════════════════════════════════════════════════════════
    print("\n" + "="*100)
    print("📊 ANALYSES SUR DONNÉES TRAITÉES")
    print("="*100 + "\n")
    
    # Analyse temporelle approfondie (trimestres, mois, années fiscales)
    temporal_stats = analysis_time_series.analyze_temporal_data(df_processed)
    
    # ════════════════════════════════════════════════════════════════
    # ANALYSES PAR GRANULARITÉ (Mois/Trimestre/Année)
    # ════════════════════════════════════════════════════════════════
    
    # Analyse des familles de produits (ABC, segmentation) - VERSION GLOBALE
    print("\n📦 Analyse produits - VERSION GLOBALE")
    family_analysis = analysis_products.analyze_product_families(df_processed)
    
    # Analyse géographique (pays, zones, scoring) - VERSION GLOBALE
    print("\n🌍 Analyse géographique - VERSION GLOBALE")
    geo_analysis = analysis_geographic.analyze_geographic_data(df_processed)
    
    # DEBUG: Afficher les clés et types
    print("\n🔍 DEBUG GÉOGRAPHIQUE:")
    for key, value in geo_analysis.items():
        if hasattr(value, 'shape'):
            print(f"   {key}: DataFrame {value.shape} - {len(value)} rows")
        else:
            print(f"   {key}: {type(value)}")
    
    print("\n" + "="*100)
    print("✅ ANALYSES TERMINÉES")
    print("="*100 + "\n")
    
    # ════════════════════════════════════════════════════════════════
    # PARTIE 2 : GÉNÉRATION DES GRAPHIQUES PAR PÉRIODE
    # ════════════════════════════════════════════════════════════════
    print("🔄 Génération des graphiques par période...")
    
    # Analyse globale (toutes périodes) - utilise granularité mensuelle par défaut
    stat_analytics_all = analysis_by_period.generate_period_analysis(df_processed, granularity='month')
    
    # 2. Obtenir les périodes disponibles
    available_periods = data_processing.get_available_periods(df_processed)
    print(f"\n📅 Périodes disponibles:")
    print(f"   • Mois: {len(available_periods['months'])} périodes")
    print(f"   • Trimestres: {len(available_periods['quarters'])} périodes")
    print(f"   • Années fiscales: {len(available_periods['fiscal_years'])} périodes")
    
    # 3. Analyses statistiques ET TEMPORELLES PAR PÉRIODE
    # Par défaut, prendre la dernière période disponible de chaque type
    
    # MOIS : Analyse avec agrégation MENSUELLE (tous les mois)
    print(f"\n📊 Génération analyse MENSUELLE (toutes les données agrégées par mois)")
    stat_analytics_month = analysis_by_period.generate_period_analysis(df_processed, granularity='month', skip_preprocessing=True)
    temp_analytics_month = analysis_time_series.generate_temporal_analysis(df_processed)
    selected_month = None
    
    # TRIMESTRE : Analyse avec agrégation TRIMESTRIELLE (tous les trimestres fiscaux)
    print(f"\n📊 Génération analyse TRIMESTRIELLE (toutes les données agrégées par trimestre fiscal)")
    stat_analytics_quarter = analysis_by_period.generate_period_analysis(df_processed, granularity='quarter', skip_preprocessing=True)
    temp_analytics_quarter = analysis_time_series.generate_temporal_analysis(df_processed)
    selected_quarter = None
    
    # ANNÉE FISCALE : Analyse avec agrégation ANNUELLE (toutes les années fiscales)
    print(f"\n📊 Génération analyse ANNUELLE (toutes les données agrégées par année fiscale)")
    stat_analytics_fiscal = analysis_by_period.generate_period_analysis(df_processed, granularity='year', skip_preprocessing=True)
    temp_analytics_fiscal = analysis_time_series.generate_temporal_analysis(df_processed)
    selected_fiscal = None
    
    # ════════════════════════════════════════════════════════════════
    # ANALYSES PRODUITS PAR GRANULARITÉ
    # ════════════════════════════════════════════════════════════════
    print("\n" + "="*100)
    print("📦 ANALYSES PRODUITS PAR GRANULARITÉ")
    print("="*100)
    
    print(f"\n📦 Analyse produits - MENSUELLE")
    family_analysis_month = analysis_products.analyze_product_families(df_processed, granularity='month')
    
    print(f"\n📦 Analyse produits - TRIMESTRIELLE")
    family_analysis_quarter = analysis_products.analyze_product_families(df_processed, granularity='quarter')
    
    print(f"\n📦 Analyse produits - ANNUELLE")
    family_analysis_fiscal = analysis_products.analyze_product_families(df_processed, granularity='year')
    
    # ════════════════════════════════════════════════════════════════
    # ANALYSES GÉOGRAPHIQUES PAR GRANULARITÉ
    # ════════════════════════════════════════════════════════════════
    print("\n" + "="*100)
    print("🌍 ANALYSES GÉOGRAPHIQUES PAR GRANULARITÉ")
    print("="*100)
    
    print(f"\n🌍 Analyse géographique - MENSUELLE")
    geo_analysis_month = analysis_geographic.analyze_geographic_data(df_processed, granularity='month')
    
    print(f"\n🌍 Analyse géographique - TRIMESTRIELLE")
    geo_analysis_quarter = analysis_geographic.analyze_geographic_data(df_processed, granularity='quarter')
    
    print(f"\n🌍 Analyse géographique - ANNUELLE")
    geo_analysis_fiscal = analysis_geographic.analyze_geographic_data(df_processed, granularity='year')
    
    # 4. Analyse temporelle complète
    temp_analytics = analysis_time_series.generate_temporal_analysis(df_processed)
    
    # 5. Métriques temporelles (mensuel par défaut)
    temporal_metrics = analysis_time_series.get_temporal_metrics(df_processed, granularity='month')
    
    # Fusionner les résultats classiques (utiliser la version globale par défaut)
    all_results = {**stat_analytics_all.get('results', {}), **temp_analytics.get('results', {})}
    all_graphs = {**stat_analytics_all.get('graphs', {}), **temp_analytics.get('graphs', {})}
    all_kpis = stat_analytics_all.get('kpis', {})
    
    print("✅ Graphiques générés\n")
    
    # ════════════════════════════════════════════════════════════════
    # PARTIE 7 : ANALYSE DE LA DÉPENDANCE AUX DEVISES
    # ════════════════════════════════════════════════════════════════
    print("\n" + "="*100)
    print("💱 ANALYSE DE LA DÉPENDANCE AUX DEVISES (VERSION GLOBALE)")
    print("="*100 + "\n")
    
    currency_kpi = {}
    currency_charts = {}
    
    try:
        # Analyse complète de dépendance aux devises - VERSION GLOBALE
        currency_report = analysis_currency_dependency.analyze_currency_dependency(df_processed, output_dir=None)
        
        if 'error' not in currency_report.get('kpi', {}):
            currency_kpi = currency_report.get('kpi', {})
            currency_charts = currency_report.get('charts', {})
            
            print(f"✅ Analyse devise terminée")
            print(f"   CA Total: {currency_kpi.get('total_revenue', 0):,.0f} €")
            print(f"   Devises détectées: {len(currency_kpi.get('currencies_detected', []))}")
            print(f"   Part non-EUR: {currency_kpi.get('non_eur_pct', 0):.1f}%")
            print(f"   HHI: {currency_kpi.get('hhi_currency', 0):.0f}")
        else:
            print(f"⚠️ Erreur analyse devise: {currency_report['kpi'].get('error')}")
    except Exception as e:
        print(f"⚠️ Erreur lors de l'analyse de dépendance aux devises: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # ════════════════════════════════════════════════════════════════
    # ANALYSES DEVISES PAR GRANULARITÉ
    # ════════════════════════════════════════════════════════════════
    print("\n" + "="*100)
    print("💱 ANALYSES DEVISES PAR GRANULARITÉ")
    print("="*100)
    
    # Génération des 3 analyses par granularité
    try:
        print(f"\n💱 Analyse devises - MENSUELLE")
        currency_report_month = analysis_currency_dependency.analyze_currency_dependency(df_processed, output_dir=None, granularity='month')
        currency_kpi_month = currency_report_month.get('kpi', {})
        currency_charts_month = currency_report_month.get('charts', {})
        
        print(f"\n💱 Analyse devises - TRIMESTRIELLE")
        currency_report_quarter = analysis_currency_dependency.analyze_currency_dependency(df_processed, output_dir=None, granularity='quarter')
        currency_kpi_quarter = currency_report_quarter.get('kpi', {})
        currency_charts_quarter = currency_report_quarter.get('charts', {})
        
        print(f"\n💱 Analyse devises - ANNUELLE")
        currency_report_fiscal = analysis_currency_dependency.analyze_currency_dependency(df_processed, output_dir=None, granularity='year')
        currency_kpi_fiscal = currency_report_fiscal.get('kpi', {})
        currency_charts_fiscal = currency_report_fiscal.get('charts', {})
    except Exception as e:
        print(f"⚠️ Erreur lors de l'analyse de dépendance aux devises par granularité: {str(e)}")
        # Fallback sur l'analyse globale
        currency_kpi_month = currency_kpi
        currency_charts_month = currency_charts
        currency_kpi_quarter = currency_kpi
        currency_charts_quarter = currency_charts
        currency_kpi_fiscal = currency_kpi
        currency_charts_fiscal = currency_charts
    
    # ════════════════════════════════════════════════════════════════
    # ANALYSE DES DÉLAIS DE LIVRAISON (LEAD TIME)
    # ════════════════════════════════════════════════════════════════
    print("\n" + "="*100)
    print("⏱️ ANALYSE DES DÉLAIS DE LIVRAISON")
    print("="*100 + "\n")
    
    # Import des nouveaux services
    from .services import aggregations, insights, periods
    import json
    
    # Normaliser la période depuis le query param
    period_param = request.GET.get('period', 'month')
    period = periods.normalize_period(period_param)
    
    # Analyse des délais
    try:
        lead_time_analysis = aggregations.lead_time_pack(df_processed, period=period)
        lead_time_interpretation = insights.explain_lead_time(lead_time_analysis)
        
        # Convertir en JSON pour Chart.js
        lead_time_dist_json = json.dumps(lead_time_analysis.get('distribution', []))
        lead_time_series_json = json.dumps(lead_time_analysis.get('series_over_time', []))
        
        print(f"✅ Analyse lead time terminée")
        print(f"   Médiane: {lead_time_analysis.get('median', 0):.1f} jours")
        print(f"   % anomalies: {lead_time_analysis.get('pct_anomalies', 0):.1f}%")
    except Exception as e:
        print(f"⚠️ Erreur lors de l'analyse des délais: {str(e)}")
        import traceback
        traceback.print_exc()
        lead_time_analysis = {'error': str(e)}
        lead_time_interpretation = insights.explain_lead_time(lead_time_analysis)
        lead_time_dist_json = '[]'
        lead_time_series_json = '[]'
    
    # ════════════════════════════════════════════════════════════════
    # CONTEXTE FINAL : COMBINER TOUT
    # ════════════════════════════════════════════════════════════════
    context = {
        'dataset': dataset,
        # Ancien système (graphiques, etc.) - VERSION GLOBALE
        'results': all_results,
        'graphs': all_graphs,
        'kpis': all_kpis,
        'temporal_metrics': temporal_metrics,
        # === NOUVELLES DONNÉES PAR PÉRIODE ===
        # Périodes disponibles
        'available_periods': available_periods,
        # Analyses par période - STATISTIQUES (agrégation selon granularité)
        'results_month': {**stat_analytics_month.get('results', {}), **temp_analytics_month.get('results', {})},
        'graphs_month': {**stat_analytics_month.get('graphs', {}), **temp_analytics_month.get('graphs', {})},
        'kpis_month': stat_analytics_month.get('kpis', {}),
        'results_quarter': {**stat_analytics_quarter.get('results', {}), **temp_analytics_quarter.get('results', {})},
        'graphs_quarter': {**stat_analytics_quarter.get('graphs', {}), **temp_analytics_quarter.get('graphs', {})},
        'kpis_quarter': stat_analytics_quarter.get('kpis', {}),
        'results_fiscal': {**stat_analytics_fiscal.get('results', {}), **temp_analytics_fiscal.get('results', {})},
        'graphs_fiscal': {**stat_analytics_fiscal.get('graphs', {}), **temp_analytics_fiscal.get('graphs', {})},
        'kpis_fiscal': stat_analytics_fiscal.get('kpis', {}),
        # === FIN NOUVELLES DONNÉES ===
        # Nouveau système (analyses temporelles approfondies)
        'df_processed': df_processed,
        'temporal_stats': temporal_stats,
        'stats_trimestre': temporal_stats.get('trimestre'),
        'stats_mois': temporal_stats.get('mois'),
        'stats_annee_fiscale': temporal_stats.get('annee_fiscale'),
        'n_lignes': len(df_processed),
        'n_colonnes': len(df_processed.columns),
        'date_min': df_processed['Date Fact.'].min() if 'Date Fact.' in df_processed.columns else None,
        'date_max': df_processed['Date Fact.'].max() if 'Date Fact.' in df_processed.columns else None,
        # Analyse des familles de produits
        'family_analysis': family_analysis,
        'stats_famille': family_analysis.get('stats_famille'),
        'abc_summary': family_analysis.get('abc_summary'),
        'classe_a': family_analysis.get('classe_a'),
        'classe_b': family_analysis.get('classe_b'),
        'classe_c': family_analysis.get('classe_c'),
        # Valeurs ABC pour les cartes
        'classe_a_nb': family_analysis.get('classe_a_nb'),
        'classe_a_ca': family_analysis.get('classe_a_ca'),
        'classe_a_part': family_analysis.get('classe_a_part'),
        'classe_b_nb': family_analysis.get('classe_b_nb'),
        'classe_b_ca': family_analysis.get('classe_b_ca'),
        'classe_b_part': family_analysis.get('classe_b_part'),
        'classe_c_nb': family_analysis.get('classe_c_nb'),
        'classe_c_ca': family_analysis.get('classe_c_ca'),
        'classe_c_part': family_analysis.get('classe_c_part'),
        # Graphiques familles
        'family_graphs': family_analysis.get('family_graphs', {}),
        # === ANALYSES PRODUITS PAR GRANULARITÉ ===
        'family_analysis_month': family_analysis_month,
        'family_analysis_quarter': family_analysis_quarter,
        'family_analysis_fiscal': family_analysis_fiscal,
        # Analyse géographique - Conversion des DataFrames en listes de dicts
        'geo_analysis': geo_analysis,
        'stats_pays': geo_analysis.get('stats_pays', pd.DataFrame()).to_dict('records') if not geo_analysis.get('stats_pays', pd.DataFrame()).empty else [],
        'stats_zone': geo_analysis.get('stats_zone', pd.DataFrame()).to_dict('records') if not geo_analysis.get('stats_zone', pd.DataFrame()).empty else [],
        'classif_summary': geo_analysis.get('classif_summary', pd.DataFrame()).to_dict('records') if not geo_analysis.get('classif_summary', pd.DataFrame()).empty else [],
        'top10_score': geo_analysis.get('top10_score', pd.DataFrame()).to_dict('records') if not geo_analysis.get('top10_score', pd.DataFrame()).empty else [],
        'geo_graphs': geo_analysis.get('geo_graphs', {}),
        # === ANALYSES GÉOGRAPHIQUES PAR GRANULARITÉ ===
        'geo_analysis_month': {
            'stats_zone': geo_analysis_month.get('stats_zone', pd.DataFrame()).to_dict('records') if not geo_analysis_month.get('stats_zone', pd.DataFrame()).empty else [],
            'stats_pays': geo_analysis_month.get('stats_pays', pd.DataFrame()).to_dict('records') if not geo_analysis_month.get('stats_pays', pd.DataFrame()).empty else [],
            'classif_summary': geo_analysis_month.get('classif_summary', pd.DataFrame()).to_dict('records') if not geo_analysis_month.get('classif_summary', pd.DataFrame()).empty else [],
            'top10_score': geo_analysis_month.get('top10_score', pd.DataFrame()).to_dict('records') if not geo_analysis_month.get('top10_score', pd.DataFrame()).empty else [],
            'geo_graphs': geo_analysis_month.get('geo_graphs', {}),
        },
        'geo_analysis_quarter': {
            'stats_zone': geo_analysis_quarter.get('stats_zone', pd.DataFrame()).to_dict('records') if not geo_analysis_quarter.get('stats_zone', pd.DataFrame()).empty else [],
            'stats_pays': geo_analysis_quarter.get('stats_pays', pd.DataFrame()).to_dict('records') if not geo_analysis_quarter.get('stats_pays', pd.DataFrame()).empty else [],
            'classif_summary': geo_analysis_quarter.get('classif_summary', pd.DataFrame()).to_dict('records') if not geo_analysis_quarter.get('classif_summary', pd.DataFrame()).empty else [],
            'top10_score': geo_analysis_quarter.get('top10_score', pd.DataFrame()).to_dict('records') if not geo_analysis_quarter.get('top10_score', pd.DataFrame()).empty else [],
            'geo_graphs': geo_analysis_quarter.get('geo_graphs', {}),
        },
        'geo_analysis_fiscal': {
            'stats_zone': geo_analysis_fiscal.get('stats_zone', pd.DataFrame()).to_dict('records') if not geo_analysis_fiscal.get('stats_zone', pd.DataFrame()).empty else [],
            'stats_pays': geo_analysis_fiscal.get('stats_pays', pd.DataFrame()).to_dict('records') if not geo_analysis_fiscal.get('stats_pays', pd.DataFrame()).empty else [],
            'classif_summary': geo_analysis_fiscal.get('classif_summary', pd.DataFrame()).to_dict('records') if not geo_analysis_fiscal.get('classif_summary', pd.DataFrame()).empty else [],
            'top10_score': geo_analysis_fiscal.get('top10_score', pd.DataFrame()).to_dict('records') if not geo_analysis_fiscal.get('top10_score', pd.DataFrame()).empty else [],
            'geo_graphs': geo_analysis_fiscal.get('geo_graphs', {}),
        },
        # Analyse de dépendance aux devises
        'currency_kpi': currency_kpi,
        'currency_charts': currency_charts,
        # === ANALYSES DEVISES PAR GRANULARITÉ ===
        'currency_kpi_month': currency_kpi_month,
        'currency_charts_month': currency_charts_month,
        'currency_kpi_quarter': currency_kpi_quarter,
        'currency_charts_quarter': currency_charts_quarter,
        'currency_kpi_fiscal': currency_kpi_fiscal,
        'currency_charts_fiscal': currency_charts_fiscal,
        # === ANALYSE DES DÉLAIS ===
        'period': period,
        'lead_time_analysis': lead_time_analysis,
        'lead_time_interpretation': lead_time_interpretation,
        'lead_time_dist_json': lead_time_dist_json,
        'lead_time_series_json': lead_time_series_json,
    }
    
    # DEBUG: Afficher les données converties
    print("\n🔍 DEBUG CONTEXTE:")
    print(f"   stats_pays: {len(context['stats_pays'])} items")
    print(f"   stats_zone: {len(context['stats_zone'])} items")
    print(f"   classif_summary: {len(context['classif_summary'])} items")
    print(f"   top10_score: {len(context['top10_score'])} items")
    if context['stats_pays']:
        print(f"   Premier pays: {context['stats_pays'][0].get('Pays', 'N/A')}")
    if context['stats_zone']:
        print(f"   Première zone: {context['stats_zone'][0].get('Zone', 'N/A')}")
    
    return render(request, 'client_analytics/stats.html', context)


def clustering(request, pk):
    """Clustering page"""
    dataset = get_object_or_404(Dataset, pk=pk)
    
    # Load dataframe (already processed during upload in forms.py)
    df = dataset_io.load_dataset_df(dataset)
    
    if df is None:
        messages.error(request, 'Erreur lors du chargement du dataset')
        return redirect('client_analytics:home')
    
    # Get numeric columns
    overview_analysis = analysis_overview.generate_overview_analysis(df)
    column_types = overview_analysis.get('column_types', {})
    numeric_columns = column_types.get('numeric', [])
    
    results = None
    
    if request.method == 'POST':
        feature_columns = request.POST.getlist('feature_columns')
        n_clusters = int(request.POST.get('n_clusters', 3))
        standardize = request.POST.get('standardize') == 'on'
        
        if not feature_columns:
            messages.error(request, 'Veuillez sélectionner au moins une variable')
        else:
            # Perform clustering using analysis_clustering
            clustering_result = analysis_clustering.generate_clustering_analysis(
                df[feature_columns + ['Cpt Client']].dropna() if 'Cpt Client' in df.columns else df[feature_columns].dropna()
            )
            
            results = {
                'success': True,
                'cluster_labels': clustering_result.get('results', {}).get('cluster_stats', {}),
                'graphs': clustering_result.get('graphs', {}),
                'kpis': clustering_result.get('kpis', {}),
            }
            
            if results['success']:
                # Store results in session for export
                request.session['clustering_results'] = {
                    'dataset_pk': pk,
                    'cluster_labels': results['cluster_labels'],
                    'valid_indices': results['valid_indices'],
                }
                messages.success(request, 'Clustering effectué avec succès!')
            else:
                messages.error(request, f'Erreur: {results["error"]}')
    
    context = {
        'dataset': dataset,
        'numeric_columns': numeric_columns,
        'results': results,
    }
    return render(request, 'client_analytics/clustering.html', context)


def clustering_export(request, pk):
    """Export clustering results to CSV"""
    dataset = get_object_or_404(Dataset, pk=pk)
    
    # Get clustering results from session
    clustering_results = request.session.get('clustering_results')
    
    if not clustering_results or clustering_results['dataset_pk'] != pk:
        messages.error(request, 'Aucun résultat de clustering trouvé. Veuillez effectuer un clustering d\'abord.')
        return redirect('client_analytics:clustering', pk=pk)
    
    # Load dataframe
    df = dataset_io.load_dataset_df(dataset)
    
    if df is None:
        messages.error(request, 'Erreur lors du chargement du dataset')
        return redirect('client_analytics:home')
    
    # Add cluster labels to dataframe (simplifié)
    df_export = df.copy()
    # L'export sera géré différemment maintenant
    messages.info(request, 'Fonctionnalité d\'export en cours de mise à jour')
    return redirect('client_analytics:clustering', pk=pk)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{dataset.name}_clustering.csv"'
    
    df_export.to_csv(response, index=False)
    
    return response

# === COPILOT: BEGIN NEW VIEWS ===
# === COPILOT: END NEW VIEWS ===
