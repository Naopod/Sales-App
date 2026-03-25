from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from .models import Dataset
from .forms import UploadDatasetForm, SelectDatasetForm
from .services import dataset_io, data_processing, analysis_currency_dependency
from .services import (
    analysis_overview,
    analysis_by_period,
    analysis_time_series,
    analysis_clustering,
)
from .services import analysis_products, analysis_geographic, analysis_clients
from .services import analysis_anomalies
from .services import anomaly_detection
from .services.visualizations.viz_by_period import create_isolation_forest_time_anomaly_plot
import pandas as pd

import logging

logger = logging.getLogger(__name__)


def home(request):
    """Home page with upload and selection forms"""
    upload_form = UploadDatasetForm()
    select_form = SelectDatasetForm()

    if request.method == "POST":
        if "upload" in request.POST:
            upload_form = UploadDatasetForm(request.POST, request.FILES)
            if upload_form.is_valid():
                dataset = upload_form.save()
                messages.success(
                    request, f'Dataset "{dataset.name}" uploadé avec succès!'
                )
                return redirect("client_analytics:dataset_overview", pk=dataset.pk)

        elif "select" in request.POST:
            select_form = SelectDatasetForm(request.POST)
            if select_form.is_valid():
                dataset = select_form.cleaned_data["existing_dataset"]
                return redirect("client_analytics:dataset_overview", pk=dataset.pk)

    context = {
        "upload_form": upload_form,
        "select_form": select_form,
    }
    return render(request, "client_analytics/home.html", context)


def workflow(request):
    """Workflow explanation page"""
    return render(request, "client_analytics/workflow.html")


def dataset_overview(request, pk):
    """Dataset overview page"""
    dataset = get_object_or_404(Dataset, pk=pk)

    # Load dataframe (already processed during upload in forms.py)
    df = dataset_io.load_dataset_df(dataset)

    if df is None:
        messages.error(request, "Erreur lors du chargement du dataset")
        return redirect("client_analytics:home")

    # Get dataset info using analysis_overview
    overview_analysis = analysis_overview.generate_overview_analysis(df)
    info = overview_analysis.get("info", {})
    missing_info = overview_analysis.get("missing_info", [])
    numeric_summary = overview_analysis.get("numeric_summary")
    column_types = overview_analysis.get("column_types", {})

    # Convert dataframe head to HTML
    df_head_html = df.head(10).to_html(
        classes="table table-striped table-sm", index=False
    )

    # Convert numeric summary to HTML
    numeric_summary_html = None
    if numeric_summary is not None:
        numeric_summary_html = numeric_summary.to_html(
            classes="table table-striped table-sm"
        )

    context = {
        "dataset": dataset,
        "info": info,
        "missing_info": missing_info,
        "df_head_html": df_head_html,
        "numeric_summary_html": numeric_summary_html,
        "column_types": column_types,
    }
    return render(request, "client_analytics/dataset_overview.html", context)


def stats(request, pk):
    """Statistics page - High Tech 2024 Analytics COMPLET + Nouvelles Analyses Temporelles"""
    dataset = get_object_or_404(Dataset, pk=pk)

    # ═══════════════════════════════════════════════════════════════════
    # 📊 LECTURE DES PARAMÈTRES DEPUIS L'URL
    # ═══════════════════════════════════════════════════════════════════
    granularity_param = request.GET.get("granularity", "month")
    active_tab = request.GET.get(
        "tab", "statistics"
    )  # statistics, temporal, products, clients, geographic, currency
    selected_client = request.GET.get("client", "")
    selected_product = request.GET.get("product", "")
    selected_family = request.GET.get("family", "")

    compare_products = request.GET.getlist("compare_products")
    compare_families = request.GET.getlist("compare_families")
    compare_products_metric = request.GET.get("compare_products_metric", "Qty_Total")
    compare_families_metric = request.GET.get("compare_families_metric", "Qty_Total")

    # Normalisation et validation
    if granularity_param in ["fiscal_year", "fiscal"]:
        granularity = "year"
    elif granularity_param in ["month", "quarter", "year"]:
        granularity = granularity_param
    else:
        granularity = "month"  # Valeur par défaut si invalide

    # ═══════════════════════════════════════════════════════════════════
    # 📊 CHARGEMENT DES DONNÉES DÉJÀ TRAITÉES
    # ═══════════════════════════════════════════════════════════════════

    df_processed = dataset_io.load_dataset_df(dataset)

    if df_processed is None:
        messages.error(request, "Erreur lors du chargement du dataset")
        return redirect("client_analytics:home")

    # ════════════════════════════════════════════════════════════════
    # OPTIMISATION : Ne calculer QUE ce qui est nécessaire
    # ════════════════════════════════════════════════════════════════

    # Initialiser toutes les variables (vides par défaut)
    temporal_stats = {}
    client_analysis = {}
    available_periods = {}
    client_options = []
    client_portfolio = None
    client_portfolio_month = None
    client_portfolio_quarter = None
    client_portfolio_fiscal = None

    # ════════════════════════════════════════════════════════════════
    # CALCUL DES KPI GLOBAUX (toujours nécessaires pour l'affichage)
    # ════════════════════════════════════════════════════════════════
    global_kpis = {
        "total_transactions": int(len(df_processed)),
        "ca_total": f"{df_processed['Montant'].sum():,.2f} €",
        "nb_clients": int(df_processed["Cpt Client"].nunique()),
        "nb_familles": (
            int(df_processed["Famille"].nunique())
            if "Famille" in df_processed.columns
            else 0
        ),
        "panier_moyen": f"{df_processed['Montant'].mean():,.2f} €",
        "nb_pays": (
            int(df_processed["Pays"].nunique()) if "Pays" in df_processed.columns else 0
        ),
        "ca_moyen_client": (
            float(df_processed["Montant"].sum() / df_processed["Cpt Client"].nunique())
            if "Cpt Client" in df_processed.columns
            and df_processed["Cpt Client"].nunique()
            else None
        ),
    }

    stat_analytics_month = {"results": {}, "graphs": {}, "kpis": {}}
    stat_analytics_quarter = {"results": {}, "graphs": {}, "kpis": {}}
    stat_analytics_fiscal = {"results": {}, "graphs": {}, "kpis": {}}
    family_analysis_fiscal = {}
    geo_analysis_month = {
        "stats_zone": pd.DataFrame(),
        "stats_pays": pd.DataFrame(),
        "classif_summary": pd.DataFrame(),
        "top10_score": pd.DataFrame(),
        "geo_graphs": {},
    }
    geo_analysis_quarter = {
        "stats_zone": pd.DataFrame(),
        "stats_pays": pd.DataFrame(),
        "classif_summary": pd.DataFrame(),
        "top10_score": pd.DataFrame(),
        "geo_graphs": {},
    }
    geo_analysis_fiscal = {
        "stats_zone": pd.DataFrame(),
        "stats_pays": pd.DataFrame(),
        "classif_summary": pd.DataFrame(),
        "top10_score": pd.DataFrame(),
        "geo_graphs": {},
    }
    currency_kpi_month = {}
    currency_charts_month = {}
    currency_kpi_quarter = {}
    currency_charts_quarter = {}
    temp_analytics_month = {"results": {}, "graphs": {}}
    temp_analytics_quarter = {"results": {}, "graphs": {}}
    temp_analytics_fiscal = {"results": {}, "graphs": {}}
    family_analysis_month = {}
    family_analysis_quarter = {}
    family_analysis_year = {}
    family_analysis_fiscal = {}
    geo_analysis_month = {
        "stats_zone": pd.DataFrame(),
        "stats_pays": pd.DataFrame(),
        "classif_summary": pd.DataFrame(),
        "top10_score": pd.DataFrame(),
        "geo_graphs": {},
    }
    geo_analysis_quarter = {
        "stats_zone": pd.DataFrame(),
        "stats_pays": pd.DataFrame(),
        "classif_summary": pd.DataFrame(),
        "top10_score": pd.DataFrame(),
        "geo_graphs": {},
    }
    geo_analysis_fiscal = {
        "stats_zone": pd.DataFrame(),
        "stats_pays": pd.DataFrame(),
        "classif_summary": pd.DataFrame(),
        "top10_score": pd.DataFrame(),
        "geo_graphs": {},
    }
    currency_kpi_month = {}
    currency_charts_month = {}
    currency_kpi_quarter = {}
    currency_charts_quarter = {}
    currency_kpi_fiscal = {}
    currency_charts_fiscal = {}

    # ════════════════════════════════════════════════════════════════
    # ANALYSE CLIENTS (CALCULÉE UNE FOIS AU CHARGEMENT INITIAL)
    # ════════════════════════════════════════════════════════════════
    # Les onglets sont maintenant gérés côté client (pas de rechargement).
    # On calcule donc tout au chargement initial pour que le contenu soit disponible.
    try:
        client_analysis = analysis_clients.analyze_clients(
            df_processed, time_granularity=granularity
        )
    except Exception as e:
        logger.exception("[clients] ERROR in view")
        client_analysis = {"error": str(e), "client_graphs": {}}

    # Client 360 (portefeuille complet) - via GET param ?client=...
    try:
        client_options = analysis_clients.get_client_options(
            df_processed, max_clients=500
        )
    except Exception as e:
        logger.exception("[client360] ERROR get_client_options in view")
        client_options = []
    
    # Lire le slicer Famille (multi-select)
    selected_client_families = request.GET.getlist('client_families')
    
    # Calculer les options de familles pour le client sélectionné
    family_options = []
    if selected_client:
        try:
            family_col = analysis_clients._pick_col(df_processed, ['Famille', 'Famille Produit', 'Famille article', 'Famille_Produit'])
            client_col = analysis_clients._pick_col(df_processed, ['Cpt Client', 'Compte Client', 'Client', 'Code Client'])
            if family_col and client_col:
                df_client_temp = df_processed[df_processed[client_col].astype(str) == str(selected_client)]
                families = sorted(df_client_temp[family_col].dropna().unique().tolist())
                family_options = [{'value': f, 'label': f} for f in families]
        except Exception as e:
            logger.exception("[client360] ERROR getting family_options")
            family_options = []

    if selected_client:
        try:
            client_portfolio_month = analysis_clients.analyze_client_portfolio_full(
                df_processed,
                selected_client,
                time_granularity="month",
                top_n_families=8,
                top_n_products=10,
                selected_families=selected_client_families,
            )
            client_portfolio_quarter = analysis_clients.analyze_client_portfolio_full(
                df_processed,
                selected_client,
                time_granularity="quarter",
                top_n_families=8,
                top_n_products=10,
                selected_families=selected_client_families,
            )
            client_portfolio_fiscal = analysis_clients.analyze_client_portfolio_full(
                df_processed,
                selected_client,
                time_granularity="year",
                top_n_families=8,
                top_n_products=10,
                selected_families=selected_client_families,
            )

            # compat: variable historique utilisée dans le template
            client_portfolio = client_portfolio_month
        except Exception as e:
            logger.exception("[client360] ERROR analyze_client_portfolio_full in view")
            err = {
                "client_id": str(selected_client),
                "error": str(e),
                "kpis": {},
                "tables": {},
                "graphs": {},
                "alerts": [],
                "meta": {},
            }
            client_portfolio_month = err
            client_portfolio_quarter = err
            client_portfolio_fiscal = err
            client_portfolio = err

    # ════════════════════════════════════════════════════════════════
    # ANALYSE GÉOGRAPHIQUE (CALCULÉE UNE FOIS AU CHARGEMENT INITIAL)
    # ════════════════════════════════════════════════════════════════
    # Les sous-onglets géographiques sont gérés côté client.
    # On calcule les 3 granularités une fois au chargement.
    try:
        geo_analysis_month = analysis_geographic.analyze_geographic_data(
            df_processed, granularity="month"
        )
    except Exception as e:
        logger.exception("[geographic:month] ERROR in view")
        geo_analysis_month = {
            "stats_zone": pd.DataFrame(),
            "stats_pays": pd.DataFrame(),
            "classif_summary": pd.DataFrame(),
            "top10_score": pd.DataFrame(),
            "geo_graphs": {},
            "error": str(e),
        }

    try:
        geo_analysis_quarter = analysis_geographic.analyze_geographic_data(
            df_processed, granularity="quarter"
        )
    except Exception as e:
        logger.exception("[geographic:quarter] ERROR in view")
        geo_analysis_quarter = {
            "stats_zone": pd.DataFrame(),
            "stats_pays": pd.DataFrame(),
            "classif_summary": pd.DataFrame(),
            "top10_score": pd.DataFrame(),
            "geo_graphs": {},
            "error": str(e),
        }

    try:
        geo_analysis_fiscal = analysis_geographic.analyze_geographic_data(
            df_processed, granularity="year"
        )
    except Exception as e:
        logger.exception("[geographic:year] ERROR in view")
        geo_analysis_fiscal = {
            "stats_zone": pd.DataFrame(),
            "stats_pays": pd.DataFrame(),
            "classif_summary": pd.DataFrame(),
            "top10_score": pd.DataFrame(),
            "geo_graphs": {},
            "error": str(e),
        }

    # ════════════════════════════════════════════════════════════════
    # ANALYSE DEVISES (CALCULÉE UNE FOIS AU CHARGEMENT INITIAL)
    # ════════════════════════════════════════════════════════════════
    # Le template affiche les 3 granularités. Calcul unique au chargement.
    try:
        currency_report_month = (
            analysis_currency_dependency.analyze_currency_dependency(
                df_processed, output_dir=None, granularity="month"
            )
        )
        currency_kpi_month = currency_report_month.get("kpi", {})
        currency_charts_month = currency_report_month.get("charts", {})
    except Exception as e:
        logger.exception("[currency:month] ERROR in view")
        currency_kpi_month = {}
        currency_charts_month = {}

    try:
        currency_report_quarter = (
            analysis_currency_dependency.analyze_currency_dependency(
                df_processed, output_dir=None, granularity="quarter"
            )
        )
        currency_kpi_quarter = currency_report_quarter.get("kpi", {})
        currency_charts_quarter = currency_report_quarter.get("charts", {})
    except Exception as e:
        logger.exception("[currency:quarter] ERROR in view")
        currency_kpi_quarter = {}
        currency_charts_quarter = {}

    try:
        currency_report_fiscal = (
            analysis_currency_dependency.analyze_currency_dependency(
                df_processed, output_dir=None, granularity="year"
            )
        )
        currency_kpi_fiscal = currency_report_fiscal.get("kpi", {})
        currency_charts_fiscal = currency_report_fiscal.get("charts", {})
    except Exception as e:
        logger.exception("[currency:year] ERROR in view")
        currency_kpi_fiscal = {}
        currency_charts_fiscal = {}

    # ════════════════════════════════════════════════════════════════
    # ANALYSES PAR PÉRIODE ET TEMPORELLES (CALCULÉES AU CHARGEMENT)
    # ════════════════════════════════════════════════════════════════
    # Toutes les analyses sont calculées une fois au chargement initial.
    # Les changements d'onglets/périodes se font côté client sans rechargement.

    # Périodes disponibles
    available_periods = data_processing.get_available_periods(df_processed)

    # Cache pour analyses temporelles (calcul unique)
    try:
        df_daily_cache = analysis_time_series.aggregate_daily(df_processed)
    except Exception as e:
        logger.exception("[temporal] ERROR aggregate_daily in view")
        df_daily_cache = None

    # Cache anomalies (calcul unique)
    anomaly_report_cache = None
    if df_daily_cache is not None and not df_daily_cache.empty:
        try:
            anomaly_report_cache = anomaly_detection.build_anomaly_report(
                df_daily_cache,
                value_cols=["CA_Total", "Qty_Total", "Nb_Clients"],
            )
        except Exception:
            logger.exception("[temporal] ERROR build_anomaly_report")
            anomaly_report_cache = None

    # Analyse temporelle globale
    try:
        temporal_stats = analysis_time_series.analyze_temporal_data(df_processed)
    except Exception as e:
        logger.exception("[temporal] ERROR analyze_temporal_data in view")
        temporal_stats = {}

    # Analyses par période - MOIS
    try:
        stat_analytics_month = analysis_by_period.generate_period_analysis(
            df_processed, granularity="month", skip_preprocessing=True
        )
    except Exception as e:
        logger.exception("[statistics:month] ERROR in view")
        stat_analytics_month = {"results": {}, "graphs": {}, "kpis": {}}

    try:
        temp_analytics_month = analysis_time_series.generate_temporal_analysis(
            df_processed,
            granularity="month",
            df_daily_cache=df_daily_cache,
            anomaly_report_cache=anomaly_report_cache,
        )
    except Exception as e:
        logger.exception("[temporal:month] ERROR in view")
        temp_analytics_month = {"results": {}, "graphs": {}}

    # Analyses par période - TRIMESTRE
    try:
        stat_analytics_quarter = analysis_by_period.generate_period_analysis(
            df_processed, granularity="quarter", skip_preprocessing=True
        )
    except Exception as e:
        logger.exception("[statistics:quarter] ERROR in view")
        stat_analytics_quarter = {"results": {}, "graphs": {}, "kpis": {}}

    try:
        temp_analytics_quarter = analysis_time_series.generate_temporal_analysis(
            df_processed,
            granularity="quarter",
            df_daily_cache=df_daily_cache,
            anomaly_report_cache=anomaly_report_cache,
        )
    except Exception as e:
        logger.exception("[temporal:quarter] ERROR in view")
        temp_analytics_quarter = {"results": {}, "graphs": {}}

    # Analyses par période - ANNÉE FISCALE
    try:
        stat_analytics_fiscal = analysis_by_period.generate_period_analysis(
            df_processed, granularity="year", skip_preprocessing=True
        )
    except Exception as e:
        logger.exception("[statistics:year] ERROR in view")
        stat_analytics_fiscal = {"results": {}, "graphs": {}, "kpis": {}}

    try:
        temp_analytics_fiscal = analysis_time_series.generate_temporal_analysis(
            df_processed,
            granularity="year",
            df_daily_cache=df_daily_cache,
            anomaly_report_cache=anomaly_report_cache,
        )
    except Exception as e:
        logger.exception("[temporal:year] ERROR in view")
        temp_analytics_fiscal = {"results": {}, "graphs": {}}

    # ════════════════════════════════════════════════════════════════
    # ANALYSE PRODUITS (CALCULÉE UNE FOIS AU CHARGEMENT INITIAL)
    # ════════════════════════════════════════════════════════════════
    # Les sous-onglets Produits sont gérés côté client.
    # On calcule les 3 granularités une fois au chargement.
    try:
        family_analysis_month = analysis_products.analyze_product_families(
            df_processed,
            time_granularity="month",
            selected_product=selected_product,
            selected_family=selected_family,
            compare_products=compare_products if granularity == "month" else None,
            compare_families=compare_families if granularity == "month" else None,
            compare_products_metric=compare_products_metric,
            compare_families_metric=compare_families_metric,
            max_compare_items=5,
        )
    except Exception as e:
        logger.exception("[products:month] ERROR in view")
        family_analysis_month = {"error": str(e)}

    try:
        family_analysis_quarter = analysis_products.analyze_product_families(
            df_processed,
            time_granularity="quarter",
            selected_product=selected_product,
            selected_family=selected_family,
            compare_products=compare_products if granularity == "quarter" else None,
            compare_families=compare_families if granularity == "quarter" else None,
            compare_products_metric=compare_products_metric,
            compare_families_metric=compare_families_metric,
            max_compare_items=5,
        )
    except Exception as e:
        logger.exception("[products:quarter] ERROR in view")
        family_analysis_quarter = {"error": str(e)}

    try:
        family_analysis_year = analysis_products.analyze_product_families(
            df_processed,
            time_granularity="year",
            selected_product=selected_product,
            selected_family=selected_family,
            compare_products=compare_products if granularity == "year" else None,
            compare_families=compare_families if granularity == "year" else None,
            compare_products_metric=compare_products_metric,
            compare_families_metric=compare_families_metric,
            max_compare_items=5,
        )
    except Exception as e:
        logger.exception("[products:year] ERROR in view")
        family_analysis_year = {"error": str(e)}

    # Alias compat (anciens templates/variables)
    family_analysis_fiscal = family_analysis_year

    selected_month = None
    selected_quarter = None
    selected_fiscal = None

    # ════════════════════════════════════════════════════════════════
    # ANALYSE DES DÉLAIS DE LIVRAISON (LEAD TIME)
    # ════════════════════════════════════════════════════════════════

    # Import des nouveaux services
    from .services import aggregations, insights, periods
    import json

    # Normaliser la période depuis le query param
    period_param = request.GET.get("period", "month")
    period = periods.normalize_period(period_param)

    # ════════════════════════════════════════════════════════════════
    # SÉLECTION DES ANALYSES SELON GRANULARITÉ (pour compatibilité template)
    # ════════════════════════════════════════════════════════════════
    # Le template utilise family_analysis, geo_analysis, currency_kpi/charts
    # On utilise les versions correspondant à la granularité sélectionnée
    if granularity == "month":
        family_analysis = family_analysis_month
        geo_analysis = geo_analysis_month
        currency_kpi = currency_kpi_month
        currency_charts = currency_charts_month
        # Variables pour compatibilité avec ancien template
        all_results = {
            **stat_analytics_month.get("results", {}),
            **temp_analytics_month.get("results", {}),
        }
        all_graphs = {
            **stat_analytics_month.get("graphs", {}),
            **temp_analytics_month.get("graphs", {}),
        }
        all_kpis = {**global_kpis, **stat_analytics_month.get("kpis", {})}
    elif granularity == "quarter":
        family_analysis = family_analysis_quarter
        geo_analysis = geo_analysis_quarter
        currency_kpi = currency_kpi_quarter
        currency_charts = currency_charts_quarter
        # Variables pour compatibilité avec ancien template
        all_results = {
            **stat_analytics_quarter.get("results", {}),
            **temp_analytics_quarter.get("results", {}),
        }
        all_graphs = {
            **stat_analytics_quarter.get("graphs", {}),
            **temp_analytics_quarter.get("graphs", {}),
        }
        all_kpis = {**global_kpis, **stat_analytics_quarter.get("kpis", {})}
    else:  # year
        family_analysis = family_analysis_year
        geo_analysis = geo_analysis_fiscal
        currency_kpi = currency_kpi_fiscal
        currency_charts = currency_charts_fiscal
        # Variables pour compatibilité avec ancien template
        all_results = {
            **stat_analytics_fiscal.get("results", {}),
            **temp_analytics_fiscal.get("results", {}),
        }
        all_graphs = {
            **stat_analytics_fiscal.get("graphs", {}),
            **temp_analytics_fiscal.get("graphs", {}),
        }
        all_kpis = {**global_kpis, **stat_analytics_fiscal.get("kpis", {})}

    # Métriques temporelles (utilise la granularité sélectionnée)
    temporal_metrics = analysis_time_series.get_temporal_metrics(
        df_processed, granularity=granularity
    )

    # Analyse des délais
    try:
        lead_time_analysis = aggregations.lead_time_pack(df_processed, period=period)
        lead_time_interpretation = insights.explain_lead_time(lead_time_analysis)

        # Convertir en JSON pour Chart.js
        lead_time_dist_json = json.dumps(lead_time_analysis.get("distribution", []))
        lead_time_series_json = json.dumps(
            lead_time_analysis.get("series_over_time", [])
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        lead_time_analysis = {"error": str(e)}
        lead_time_interpretation = insights.explain_lead_time(lead_time_analysis)
        lead_time_dist_json = "[]"
        lead_time_series_json = "[]"

    # ════════════════════════════════════════════════════════════════
    # CONTEXTE FINAL : COMBINER TOUT
    # ════════════════════════════════════════════════════════════════
    context = {
        "dataset": dataset,
        # Granularité sélectionnée
        "granularity": granularity,
        # Onglet actif (pilotage template)
        "active_tab": active_tab,
        # Ancien système (graphiques, etc.) - VERSION GLOBALE
        "results": all_results,
        "graphs": all_graphs,
        "kpis": all_kpis,
        "temporal_metrics": temporal_metrics,
        # === NOUVELLES DONNÉES PAR PÉRIODE ===
        # Périodes disponibles
        "available_periods": available_periods,
        # Analyses par période - STATISTIQUES (agrégation selon granularité)
        "results_month": {
            **stat_analytics_month.get("results", {}),
            **temp_analytics_month.get("results", {}),
        },
        "graphs_month": {
            **stat_analytics_month.get("graphs", {}),
            **temp_analytics_month.get("graphs", {}),
        },
        "kpis_month": stat_analytics_month.get("kpis", {}),
        "results_quarter": {
            **stat_analytics_quarter.get("results", {}),
            **temp_analytics_quarter.get("results", {}),
        },
        "graphs_quarter": {
            **stat_analytics_quarter.get("graphs", {}),
            **temp_analytics_quarter.get("graphs", {}),
        },
        "kpis_quarter": stat_analytics_quarter.get("kpis", {}),
        "results_fiscal": {
            **stat_analytics_fiscal.get("results", {}),
            **temp_analytics_fiscal.get("results", {}),
        },
        "graphs_fiscal": {
            **stat_analytics_fiscal.get("graphs", {}),
            **temp_analytics_fiscal.get("graphs", {}),
        },
        "kpis_fiscal": stat_analytics_fiscal.get("kpis", {}),
        # === FIN NOUVELLES DONNÉES ===
        # Nouveau système (analyses temporelles approfondies)
        "df_processed": df_processed,
        "temporal_stats": temporal_stats,
        "stats_trimestre": temporal_stats.get("trimestre"),
        "stats_mois": temporal_stats.get("mois"),
        "stats_annee_fiscale": temporal_stats.get("annee_fiscale"),
        "n_lignes": len(df_processed),
        "n_colonnes": len(df_processed.columns),
        "date_min": (
            df_processed["Date Fact."].min()
            if "Date Fact." in df_processed.columns
            else None
        ),
        "date_max": (
            df_processed["Date Fact."].max()
            if "Date Fact." in df_processed.columns
            else None
        ),
        # Analyse des clients
        "client_analysis": client_analysis,
        "client_stats": client_analysis.get("client_stats"),
        "top10_clients": client_analysis.get("top10_clients"),
        "top20_clients": client_analysis.get("top20_clients"),
        "concentration_top20_pct": client_analysis.get("concentration_top20_pct"),
        "concentration_top10_pct": client_analysis.get("concentration_top10_pct"),
        "client_graphs": client_analysis.get("client_graphs", {}),
        # Client 360
        "client_options": client_options,
        "selected_client": selected_client,
        "selected_client_families": selected_client_families,
        "family_options": family_options,
        "client_portfolio": client_portfolio,
        "client_portfolio_month": client_portfolio_month,
        "client_portfolio_quarter": client_portfolio_quarter,
        "client_portfolio_fiscal": client_portfolio_fiscal,
        # Analyse des familles de produits
        "family_analysis": family_analysis,
        "stats_famille": family_analysis.get("stats_famille"),
        "abc_summary": family_analysis.get("abc_summary"),
        "classe_a": family_analysis.get("classe_a"),
        "classe_b": family_analysis.get("classe_b"),
        "classe_c": family_analysis.get("classe_c"),
        # Valeurs ABC pour les cartes
        "classe_a_nb": family_analysis.get("classe_a_nb"),
        "classe_a_ca": family_analysis.get("classe_a_ca"),
        "classe_a_part": family_analysis.get("classe_a_part"),
        "classe_b_nb": family_analysis.get("classe_b_nb"),
        "classe_b_ca": family_analysis.get("classe_b_ca"),
        "classe_b_part": family_analysis.get("classe_b_part"),
        "classe_c_nb": family_analysis.get("classe_c_nb"),
        "classe_c_ca": family_analysis.get("classe_c_ca"),
        "classe_c_part": family_analysis.get("classe_c_part"),
        # Graphiques familles
        "family_graphs": family_analysis.get("family_graphs", {}),
        # === ANALYSES PRODUITS PAR GRANULARITÉ ===
        "family_analysis_month": family_analysis_month,
        "family_analysis_quarter": family_analysis_quarter,
        "family_analysis_year": family_analysis_year,
        "family_analysis_fiscal": family_analysis_fiscal,
        # Analyse géographique - Conversion des DataFrames en listes de dicts
        "geo_analysis": geo_analysis,
        "stats_pays": (
            geo_analysis.get("stats_pays", pd.DataFrame()).to_dict("records")
            if not geo_analysis.get("stats_pays", pd.DataFrame()).empty
            else []
        ),
        "stats_zone": (
            geo_analysis.get("stats_zone", pd.DataFrame()).to_dict("records")
            if not geo_analysis.get("stats_zone", pd.DataFrame()).empty
            else []
        ),
        "classif_summary": (
            geo_analysis.get("classif_summary", pd.DataFrame()).to_dict("records")
            if not geo_analysis.get("classif_summary", pd.DataFrame()).empty
            else []
        ),
        "top10_score": (
            geo_analysis.get("top10_score", pd.DataFrame()).to_dict("records")
            if not geo_analysis.get("top10_score", pd.DataFrame()).empty
            else []
        ),
        "geo_graphs": geo_analysis.get("geo_graphs", {}),
        # === ANALYSES GÉOGRAPHIQUES PAR GRANULARITÉ ===
        "geo_analysis_month": {
            "stats_zone": (
                geo_analysis_month.get("stats_zone", pd.DataFrame()).to_dict("records")
                if not geo_analysis_month.get("stats_zone", pd.DataFrame()).empty
                else []
            ),
            "stats_pays": (
                geo_analysis_month.get("stats_pays", pd.DataFrame()).to_dict("records")
                if not geo_analysis_month.get("stats_pays", pd.DataFrame()).empty
                else []
            ),
            "classif_summary": (
                geo_analysis_month.get("classif_summary", pd.DataFrame()).to_dict(
                    "records"
                )
                if not geo_analysis_month.get("classif_summary", pd.DataFrame()).empty
                else []
            ),
            "top10_score": (
                geo_analysis_month.get("top10_score", pd.DataFrame()).to_dict("records")
                if not geo_analysis_month.get("top10_score", pd.DataFrame()).empty
                else []
            ),
            "geo_graphs": geo_analysis_month.get("geo_graphs", {}),
        },
        "geo_analysis_quarter": {
            "stats_zone": (
                geo_analysis_quarter.get("stats_zone", pd.DataFrame()).to_dict(
                    "records"
                )
                if not geo_analysis_quarter.get("stats_zone", pd.DataFrame()).empty
                else []
            ),
            "stats_pays": (
                geo_analysis_quarter.get("stats_pays", pd.DataFrame()).to_dict(
                    "records"
                )
                if not geo_analysis_quarter.get("stats_pays", pd.DataFrame()).empty
                else []
            ),
            "classif_summary": (
                geo_analysis_quarter.get("classif_summary", pd.DataFrame()).to_dict(
                    "records"
                )
                if not geo_analysis_quarter.get("classif_summary", pd.DataFrame()).empty
                else []
            ),
            "top10_score": (
                geo_analysis_quarter.get("top10_score", pd.DataFrame()).to_dict(
                    "records"
                )
                if not geo_analysis_quarter.get("top10_score", pd.DataFrame()).empty
                else []
            ),
            "geo_graphs": geo_analysis_quarter.get("geo_graphs", {}),
        },
        "geo_analysis_fiscal": {
            "stats_zone": (
                geo_analysis_fiscal.get("stats_zone", pd.DataFrame()).to_dict("records")
                if not geo_analysis_fiscal.get("stats_zone", pd.DataFrame()).empty
                else []
            ),
            "stats_pays": (
                geo_analysis_fiscal.get("stats_pays", pd.DataFrame()).to_dict("records")
                if not geo_analysis_fiscal.get("stats_pays", pd.DataFrame()).empty
                else []
            ),
            "classif_summary": (
                geo_analysis_fiscal.get("classif_summary", pd.DataFrame()).to_dict(
                    "records"
                )
                if not geo_analysis_fiscal.get("classif_summary", pd.DataFrame()).empty
                else []
            ),
            "top10_score": (
                geo_analysis_fiscal.get("top10_score", pd.DataFrame()).to_dict(
                    "records"
                )
                if not geo_analysis_fiscal.get("top10_score", pd.DataFrame()).empty
                else []
            ),
            "geo_graphs": geo_analysis_fiscal.get("geo_graphs", {}),
        },
        # Analyse de dépendance aux devises
        "currency_kpi": currency_kpi,
        "currency_charts": currency_charts,
        # === ANALYSES DEVISES PAR GRANULARITÉ ===
        "currency_kpi_month": currency_kpi_month,
        "currency_charts_month": currency_charts_month,
        "currency_kpi_quarter": currency_kpi_quarter,
        "currency_charts_quarter": currency_charts_quarter,
        "currency_kpi_fiscal": currency_kpi_fiscal,
        "currency_charts_fiscal": currency_charts_fiscal,
        # === ANALYSE DES DÉLAIS ===
        "period": period,
        "lead_time_analysis": lead_time_analysis,
        "lead_time_interpretation": lead_time_interpretation,
        "lead_time_dist_json": lead_time_dist_json,
        "lead_time_series_json": lead_time_series_json,
    }

    return render(request, "client_analytics/stats.html", context)


def anomalies(request, pk):
    """Page Détection d'Anomalies (portefeuille client)."""
    dataset = get_object_or_404(Dataset, pk=pk)

    granularity_param = request.GET.get("granularity", "month")
    if granularity_param in ["fiscal_year", "fiscal"]:
        granularity = "year"
    elif granularity_param in ["month", "quarter", "year"]:
        granularity = granularity_param
    else:
        granularity = "month"

    all_clients = (request.GET.get("all") or "").strip() in {
        "1",
        "true",
        "True",
        "yes",
        "on",
    }

    # Support multi-sélection: ?client=A&client=B ...
    selected_clients = [
        c.strip() for c in request.GET.getlist("client") if (c or "").strip()
    ]
    # rétro-compat si jamais un client unique arrive via ?client=...
    if not selected_clients:
        single = (request.GET.get("client") or "").strip()
        if single:
            selected_clients = [single]

    selected_client = selected_clients[0] if len(selected_clients) == 1 else ""

    df_processed = dataset_io.load_dataset_df(dataset)
    if df_processed is None:
        messages.error(request, "Erreur lors du chargement du dataset")
        return redirect("client_analytics:home")

    # Options pour le sélecteur client
    try:
        client_options = analysis_clients.get_client_options(
            df_processed, max_clients=500
        )
    except Exception as e:
        logger.exception("[anomalies] ERROR get_client_options")
        client_options = []

    anom = None
    if all_clients:
        try:
            anom = analysis_anomalies.analyze_client_anomalies(
                df_processed,
                time_granularity=granularity,
                z_thresh=3.5,
                include_scatter=False,
            )
        except Exception as e:
            logger.exception("[anomalies] ERROR analyze_client_anomalies")
            anom = {
                "error": str(e),
                "kpis": {},
                "top_anomalies_latest": [],
                "graphs": {},
                "meta": {},
            }

    anom_client = None
    anom_clients = []
    anom_clients_graph = None
    if selected_clients and not all_clients:
        for client_id in selected_clients:
            try:
                report = analysis_anomalies.analyze_client_anomalies_for_client(
                    df_processed,
                    client_id=client_id,
                    time_granularity=granularity,
                    z_thresh=3.5,
                )
            except Exception as e:
                logger.exception(
                    "[anomalies] ERROR analyze_client_anomalies_for_client (client=%s)",
                    client_id,
                )
                report = {"error": str(e), "client": {"id": str(client_id)}}
            anom_clients.append(report)

        if len(anom_clients) == 1:
            anom_client = anom_clients[0]

    # Graphiques (Matplotlib base64)
    try:
        from .services.visualizations.viz_anomalies_client import (
            plot_client_timeline,
            plot_multi_clients_anomaly_counts,
            plot_top_anomalies,
            plot_anomaly_scores_timeline,
        )

        if anom_client and not anom_client.get("error"):
            # Timeline des métriques avec anomalies
            png = plot_client_timeline(
                anom_client.get("series") or [],
                client_id=str(
                    ((anom_client.get("client") or {}).get("id"))
                    or selected_client
                    or ""
                ),
                granularity=granularity,
            )
            if png:
                anom_client.setdefault("graphs", {})["timeline"] = png

            # Timeline des scores d'anomalie ML
            png_scores = plot_anomaly_scores_timeline(
                anom_client.get("series") or [],
                client_id=str(
                    ((anom_client.get("client") or {}).get("id"))
                    or selected_client
                    or ""
                ),
                granularity=granularity,
            )
            if png_scores:
                anom_client.setdefault("graphs", {})["scores_ml"] = png_scores

        if len(anom_clients) > 1:
            anom_clients_graph = plot_multi_clients_anomaly_counts(
                anom_clients, granularity=granularity
            )

        if (
            all_clients
            and anom
            and not (anom.get("error") if isinstance(anom, dict) else False)
        ):
            rows = (
                (anom.get("top_anomalies_latest") or [])
                if isinstance(anom, dict)
                else []
            )
            if not rows:
                rows = (
                    (anom.get("top_anomalies_all") or [])
                    if isinstance(anom, dict)
                    else []
                )
            png = plot_top_anomalies(
                rows,
                granularity=granularity,
                title="Top anomalies (vue globale)",
            )
            if png and isinstance(anom, dict):
                anom.setdefault("graphs", {})["top_anomalies_bar"] = png
    except Exception:
        logger.exception("[anomalies] ERROR generating graphs")

    context = {
        "dataset": dataset,
        "granularity": granularity if 'granularity' in locals() else None,
        "anom": anom,
        "client_options": client_options,
        "selected_client": selected_client,
        "selected_clients": selected_clients,
        "all_clients": all_clients,
        "anom_client": anom_client,
        "anom_clients": anom_clients,
        "anom_clients_graph": anom_clients_graph,
    }

    # Ajout Isolation Forest (analyse sur le client sélectionné)
    # Analyse Isolation Forest uniquement si un client est sélectionné
    if 'selected_clients' in locals() and selected_clients and not all_clients:
        try:
            df_iforest = df_processed.copy()
            client_col = 'Client' if 'Client' in df_iforest.columns else None
            if client_col:
                df_iforest = df_iforest[df_iforest[client_col].isin(selected_clients)]
            time_col = 'Month' if 'Month' in df_iforest.columns else df_iforest.columns[0]
            value_col = 'Montant' if 'Montant' in df_iforest.columns else df_iforest.select_dtypes(include='number').columns[0]
            html_iforest, anomalies_df = create_isolation_forest_time_anomaly_plot(
                df_iforest, time_col, value_col, return_anomalies=True
            )
            context['iforest_html'] = html_iforest
            context['iforest_anomalies'] = anomalies_df.to_dict('records') if anomalies_df is not None else []
            context['iforest_time_col'] = time_col
            context['iforest_value_col'] = value_col
        except Exception as e:
            logger.exception('[anomalies] Isolation Forest error')
            context['iforest_html'] = None
            context['iforest_anomalies'] = []
            context['iforest_time_col'] = None
            context['iforest_value_col'] = None

    return render(request, "client_analytics/anomalies.html", context)


def clustering(request, pk):
    """Clustering page"""
    dataset = get_object_or_404(Dataset, pk=pk)

    # Load dataframe (already processed during upload in forms.py)
    df = dataset_io.load_dataset_df(dataset)

    if df is None:
        messages.error(request, "Erreur lors du chargement du dataset")
        return redirect("client_analytics:home")

    # Get numeric columns
    overview_analysis = analysis_overview.generate_overview_analysis(df)
    column_types = overview_analysis.get("column_types", {})
    numeric_columns = column_types.get("numeric", [])

    results = None

    if request.method == "POST":
        feature_columns = request.POST.getlist("feature_columns")
        n_clusters = int(request.POST.get("n_clusters", 3))
        standardize = request.POST.get("standardize") == "on"

        if not feature_columns:
            messages.error(request, "Veuillez sélectionner au moins une variable")
        else:
            # Perform clustering using analysis_clustering
            clustering_result = analysis_clustering.generate_clustering_analysis(
                df[feature_columns + ["Cpt Client"]].dropna()
                if "Cpt Client" in df.columns
                else df[feature_columns].dropna()
            )

            results = {
                "success": True,
                "cluster_labels": clustering_result.get("results", {}).get(
                    "cluster_stats", {}
                ),
                "graphs": clustering_result.get("graphs", {}),
                "kpis": clustering_result.get("kpis", {}),
            }

            if results["success"]:
                # Store results in session for export
                request.session["clustering_results"] = {
                    "dataset_pk": pk,
                    "cluster_labels": results["cluster_labels"],
                    "valid_indices": results["valid_indices"],
                }
                messages.success(request, "Clustering effectué avec succès!")
            else:
                messages.error(request, f'Erreur: {results["error"]}')

    context = {
        "dataset": dataset,
        "numeric_columns": numeric_columns,
        "results": results,
    }
    return render(request, "client_analytics/clustering.html", context)


def clustering_export(request, pk):
    """Export clustering results to CSV"""
    dataset = get_object_or_404(Dataset, pk=pk)

    # Get clustering results from session
    clustering_results = request.session.get("clustering_results")

    if not clustering_results or clustering_results["dataset_pk"] != pk:
        messages.error(
            request,
            "Aucun résultat de clustering trouvé. Veuillez effectuer un clustering d'abord.",
        )
        return redirect("client_analytics:clustering", pk=pk)

    # Load dataframe
    df = dataset_io.load_dataset_df(dataset)

    if df is None:
        messages.error(request, "Erreur lors du chargement du dataset")
        return redirect("client_analytics:home")

    # Add cluster labels to dataframe (simplifié)
    df_export = df.copy()
    # L'export sera géré différemment maintenant
    messages.info(request, "Fonctionnalité d'export en cours de mise à jour")
    return redirect("client_analytics:clustering", pk=pk)


# ═══════════════════════════════════════════════════════════════════
# VUES AJAX POUR ANALYSES CIBLÉES (éviter rechargement complet)
# ═══════════════════════════════════════════════════════════════════


@require_http_methods(["GET"])
def ajax_client_portfolio(request, pk):
    """AJAX: Charger le portefeuille d'un client spécifique"""
    dataset = get_object_or_404(Dataset, pk=pk)

    client_id = request.GET.get("client", "")
    granularity = request.GET.get("granularity", "month")

    if not client_id:
        return JsonResponse({"error": "Client ID manquant"}, status=400)

    df_processed = dataset_io.load_dataset_df(dataset)
    if df_processed is None:
        return JsonResponse({"error": "Erreur chargement dataset"}, status=500)

    try:
        portfolio = analysis_clients.analyze_client_portfolio_full(
            df_processed,
            client_id,
            time_granularity=granularity,
            top_n_families=8,
            top_n_products=10,
        )

        # Rendre le partial HTML et le retourner
        from django.template.loader import render_to_string

        html = render_to_string(
            "client_analytics/partials/_client360_block.html",
            {"client_portfolio": portfolio},
        )

        return JsonResponse({"success": True, "html": html})

    except Exception as e:
        logger.exception("[ajax_client_portfolio] ERROR")
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
def ajax_product_correlation(request, pk):
    """AJAX: Calculer corrélation ciblée pour produit ou famille"""
    dataset = get_object_or_404(Dataset, pk=pk)

    product = request.GET.get("product", "")
    family = request.GET.get("family", "")
    granularity = request.GET.get("granularity", "month")

    if not product and not family:
        return JsonResponse({"error": "Produit ou famille manquant"}, status=400)

    df_processed = dataset_io.load_dataset_df(dataset)
    if df_processed is None:
        return JsonResponse({"error": "Erreur chargement dataset"}, status=500)

    try:
        # Recalculer uniquement l'analyse produits avec les paramètres ciblés
        family_analysis = analysis_products.analyze_product_families(
            df_processed,
            time_granularity=granularity,
            selected_product=product,
            selected_family=family,
            compare_products=None,
            compare_families=None,
            compare_products_metric="Qty_Total",
            compare_families_metric="Qty_Total",
            max_compare_items=5,
        )

        # Extraire le graphique approprié
        family_graphs = family_analysis.get("family_graphs", {})

        if product:
            graph_html = family_graphs.get("product_corr_heatmap", "")
            if not graph_html:
                return JsonResponse(
                    {
                        "success": True,
                        "html": '<div class="alert alert-info"><i class="bi bi-info-circle"></i> Pas assez de données pour calculer une corrélation fiable pour ce produit.</div>',
                    }
                )
        elif family:
            graph_html = family_graphs.get("family_corr_heatmap", "")
            if not graph_html:
                return JsonResponse(
                    {
                        "success": True,
                        "html": '<div class="alert alert-info"><i class="bi bi-info-circle"></i> Pas assez de données pour calculer une corrélation fiable pour cette famille.</div>',
                    }
                )

        return JsonResponse({"success": True, "html": graph_html})

    except Exception as e:
        logger.exception("[ajax_product_correlation] ERROR")
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
def ajax_compare_products(request, pk):
    """AJAX: Comparer plusieurs produits"""
    dataset = get_object_or_404(Dataset, pk=pk)

    compare_products = request.GET.getlist("compare_products")
    metric = request.GET.get("compare_products_metric", "Qty_Total")
    granularity = request.GET.get("granularity", "month")

    if not compare_products:
        return JsonResponse({"error": "Aucun produit sélectionné"}, status=400)

    df_processed = dataset_io.load_dataset_df(dataset)
    if df_processed is None:
        return JsonResponse({"error": "Erreur chargement dataset"}, status=500)

    try:
        # Recalculer uniquement avec les produits à comparer
        family_analysis = analysis_products.analyze_product_families(
            df_processed,
            time_granularity=granularity,
            selected_product=None,
            selected_family=None,
            compare_products=compare_products,
            compare_families=None,
            compare_products_metric=metric,
            compare_families_metric="Qty_Total",
            max_compare_items=5,
        )

        graph_html = family_analysis.get("family_graphs", {}).get(
            "compare_products_timeseries", ""
        )

        if not graph_html:
            return JsonResponse(
                {
                    "success": True,
                    "html": '<div class="alert alert-info"><i class="bi bi-info-circle"></i> Pas de données disponibles pour cette comparaison.</div>',
                }
            )

        return JsonResponse({"success": True, "html": graph_html})

    except Exception as e:
        logger.exception("[ajax_compare_products] ERROR")
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
def ajax_compare_families(request, pk):
    """AJAX: Comparer plusieurs familles"""
    dataset = get_object_or_404(Dataset, pk=pk)

    compare_families = request.GET.getlist("compare_families")
    metric = request.GET.get("compare_families_metric", "Qty_Total")
    granularity = request.GET.get("granularity", "month")

    if not compare_families:
        return JsonResponse({"error": "Aucune famille sélectionnée"}, status=400)

    df_processed = dataset_io.load_dataset_df(dataset)
    if df_processed is None:
        return JsonResponse({"error": "Erreur chargement dataset"}, status=500)

    try:
        # Recalculer uniquement avec les familles à comparer
        family_analysis = analysis_products.analyze_product_families(
            df_processed,
            time_granularity=granularity,
            selected_product=None,
            selected_family=None,
            compare_products=None,
            compare_families=compare_families,
            compare_products_metric="Qty_Total",
            compare_families_metric=metric,
            max_compare_items=5,
        )

        graph_html = family_analysis.get("family_graphs", {}).get(
            "compare_families_timeseries", ""
        )

        if not graph_html:
            return JsonResponse(
                {
                    "success": True,
                    "html": '<div class="alert alert-info"><i class="bi bi-info-circle"></i> Pas de données disponibles pour cette comparaison.</div>',
                }
            )

        return JsonResponse({"success": True, "html": graph_html})

    except Exception as e:
        logger.exception("[ajax_compare_families] ERROR")
        return JsonResponse({"error": str(e)}, status=500)
