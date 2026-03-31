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
from .services.visualizations.viz_by_period import (
    create_isolation_forest_time_anomaly_plot,
)
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


# ─── helpers (used by stats() and ajax_tab()) ────────────────────────────────


def _normalize_granularity(param: str) -> str:
    if param in ("fiscal_year", "fiscal"):
        return "year"
    return param if param in ("month", "quarter", "year") else "month"


def _build_global_kpis(df: "pd.DataFrame") -> dict:
    nb_clients = df["Cpt Client"].nunique() if "Cpt Client" in df.columns else 0
    return {
        "total_transactions": int(len(df)),
        "ca_total": f"{df['Montant'].sum():,.2f} \u20ac",
        "nb_clients": int(nb_clients),
        "nb_familles": int(df["Famille"].nunique()) if "Famille" in df.columns else 0,
        "panier_moyen": f"{df['Montant'].mean():,.2f} \u20ac",
        "nb_pays": int(df["Pays"].nunique()) if "Pays" in df.columns else 0,
        "ca_moyen_client": (
            float(df["Montant"].sum() / nb_clients) if nb_clients else None
        ),
    }


def _safe_run(fn, *args, fallback=None, label="", **kwargs):
    """Call fn(*args, **kwargs), log exceptions and return fallback on error."""
    try:
        return fn(*args, **kwargs)
    except Exception:
        logger.exception("[%s] ERROR", label)
        return fallback if fallback is not None else {}


def _build_temporal_context(df: "pd.DataFrame", granularity: str = "month") -> dict:
    df_daily = _safe_run(
        analysis_time_series.aggregate_daily, df, label="temporal:daily"
    )
    result = _safe_run(
        analysis_time_series.generate_temporal_analysis,
        df,
        granularity=granularity,
        df_daily_cache=df_daily,
        anomaly_report_cache=None,
        label=f"temporal:{granularity}",
        fallback={"results": {}, "graphs": {}},
    )
    return {
        "results": result.get("results", {}),
        "graphs": result.get("graphs", {}),
        "granularity": granularity,
    }


def _build_products_context(
    df: "pd.DataFrame",
    granularity: str = "month",
    selected_product: str = "",
    selected_family: str = "",
) -> dict:
    result = _safe_run(
        analysis_products.analyze_product_families,
        df,
        time_granularity=granularity,
        selected_product=selected_product,
        selected_family=selected_family,
        compare_products=None,
        compare_families=None,
        compare_products_metric="Qty_Total",
        compare_families_metric="Qty_Total",
        max_compare_items=5,
        label=f"products:{granularity}",
        fallback={},
    )
    return {
        "family_analysis": result,
        "granularity": granularity,
    }


def _build_clients_context(
    df: "pd.DataFrame", granularity: str = "month", selected_client: str = ""
) -> dict:
    client_analysis = _safe_run(
        analysis_clients.analyze_clients,
        df,
        time_granularity=granularity,
        label="clients:analyze",
        fallback={},
    )
    client_options = _safe_run(
        analysis_clients.get_client_options,
        df,
        max_clients=500,
        label="clients:options",
        fallback=[],
    )

    portfolio = portfolio_m = portfolio_q = portfolio_f = None
    if selected_client:

        def _port(g):
            return _safe_run(
                analysis_clients.analyze_client_portfolio_full,
                df,
                selected_client,
                time_granularity=g,
                top_n_families=8,
                top_n_products=10,
                label=f"clients:portfolio:{g}",
                fallback={"client_id": selected_client, "kpis": {}, "graphs": {}},
            )

        portfolio_m = _port("month")
        portfolio_q = _port("quarter")
        portfolio_f = _port("year")
        portfolio = portfolio_m

    return {
        "client_analysis": client_analysis,
        "client_stats": client_analysis.get("client_stats"),
        "top10_clients": client_analysis.get("top10_clients"),
        "top20_clients": client_analysis.get("top20_clients"),
        "concentration_top20_pct": client_analysis.get("concentration_top20_pct"),
        "concentration_top10_pct": client_analysis.get("concentration_top10_pct"),
        "client_graphs": client_analysis.get("client_graphs", {}),
        "client_options": client_options,
        "selected_client": selected_client,
        "client_portfolio": portfolio,
        "client_portfolio_month": portfolio_m,
        "client_portfolio_quarter": portfolio_q,
        "client_portfolio_fiscal": portfolio_f,
    }


def _geo_analysis_to_dict(result: dict) -> dict:
    """Converts raw analyze_geographic_data result to template-ready dicts."""

    def _recs(df):
        try:
            return df.to_dict("records") if not df.empty else []
        except Exception:
            return []

    return {
        "stats_zone": _recs(result.get("stats_zone", pd.DataFrame())),
        "stats_pays": _recs(result.get("stats_pays", pd.DataFrame())),
        "classif_summary": _recs(result.get("classif_summary", pd.DataFrame())),
        "top10_score": _recs(result.get("top10_score", pd.DataFrame())),
        "geo_graphs": result.get("geo_graphs", {}),
    }


def _build_geographic_context(df: "pd.DataFrame", granularity: str = "month") -> dict:
    raw = _safe_run(
        analysis_geographic.analyze_geographic_data,
        df,
        granularity=granularity,
        label=f"geographic:{granularity}",
        fallback={
            "stats_zone": pd.DataFrame(),
            "stats_pays": pd.DataFrame(),
            "classif_summary": pd.DataFrame(),
            "top10_score": pd.DataFrame(),
            "geo_graphs": {},
        },
    )
    d = _geo_analysis_to_dict(raw)
    return {
        "stats_zone": d["stats_zone"],
        "stats_pays": d["stats_pays"],
        "classif_summary": d["classif_summary"],
        "top10_score": d["top10_score"],
        "geo_graphs": d["geo_graphs"],
        "granularity": granularity,
    }


def _build_currency_context(df: "pd.DataFrame", granularity: str = "month") -> dict:
    report = _safe_run(
        analysis_currency_dependency.analyze_currency_dependency,
        df,
        output_dir=None,
        granularity=granularity,
        label=f"currency:{granularity}",
        fallback={},
    )
    return {
        "currency_kpi": report.get("kpi", {}),
        "currency_charts": report.get("charts", {}),
        "granularity": granularity,
    }


# ─── main stats view (initial load: statistics tab only) ─────────────────────


def stats(request, pk):
    """
    Statistics dashboard.

    On initial page load only the statistics analysis is computed (the default
    tab). All other tabs are loaded lazily via the ajax_tab endpoint when the
    user first navigates to them, avoiding unnecessary computation.
    """
    dataset = get_object_or_404(Dataset, pk=pk)

    granularity = _normalize_granularity(request.GET.get("granularity", "month"))
    active_tab = request.GET.get("tab", "statistics")
    selected_client = request.GET.get("client", "")

    df_processed = dataset_io.load_dataset_df(dataset)
    if df_processed is None:
        messages.error(request, "Erreur lors du chargement du dataset")
        return redirect("client_analytics:home")

    # Global KPIs (always needed for the top cards)
    global_kpis = _build_global_kpis(df_processed)

    # Statistics analysis – the only one computed on initial load
    def _stat(g):
        return _safe_run(
            analysis_by_period.generate_period_analysis,
            df_processed,
            granularity=g,
            skip_preprocessing=True,
            label=f"statistics:{g}",
            fallback={"results": {}, "graphs": {}, "kpis": {}},
        )

    stat_m = _stat("month")
    stat_q = _stat("quarter")
    stat_y = _stat("year")

    all_kpis = {**global_kpis, **stat_m.get("kpis", {})}

    available_periods = _safe_run(
        data_processing.get_available_periods,
        df_processed,
        label="available_periods",
        fallback={},
    )
    temporal_metrics = _safe_run(
        analysis_time_series.get_temporal_metrics,
        df_processed,
        granularity=granularity,
        label="temporal_metrics",
        fallback={},
    )

    # Lead-time (optional, rendered outside the main tab panes)
    from .services import aggregations, insights, periods as period_svc
    import json

    period_param = period_svc.normalize_period(request.GET.get("period", "month"))
    lead_time_analysis = _safe_run(
        aggregations.lead_time_pack,
        df_processed,
        period=period_param,
        label="lead_time",
        fallback={"error": "N/A"},
    )
    lead_time_interpretation = insights.explain_lead_time(lead_time_analysis)
    lead_time_dist_json = json.dumps(lead_time_analysis.get("distribution", []))
    lead_time_series_json = json.dumps(lead_time_analysis.get("series_over_time", []))

    _empty_geo = {
        "stats_zone": [],
        "stats_pays": [],
        "classif_summary": [],
        "top10_score": [],
        "geo_graphs": {},
    }

    context = {
        "dataset": dataset,
        "granularity": granularity,
        "active_tab": active_tab,
        "kpis": all_kpis,
        "temporal_metrics": temporal_metrics,
        "available_periods": available_periods,
        # Statistics per granularity (stats tab content)
        "results_month": stat_m.get("results", {}),
        "graphs_month": stat_m.get("graphs", {}),
        "kpis_month": stat_m.get("kpis", {}),
        "results_quarter": stat_q.get("results", {}),
        "graphs_quarter": stat_q.get("graphs", {}),
        "kpis_quarter": stat_q.get("kpis", {}),
        "results_fiscal": stat_y.get("results", {}),
        "graphs_fiscal": stat_y.get("graphs", {}),
        "kpis_fiscal": stat_y.get("kpis", {}),
        "results": stat_m.get("results", {}),
        "graphs": stat_m.get("graphs", {}),
        # Date info
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
        "n_lignes": len(df_processed),
        "n_colonnes": len(df_processed.columns),
        # Lead-time
        "period": period_param,
        "lead_time_analysis": lead_time_analysis,
        "lead_time_interpretation": lead_time_interpretation,
        "lead_time_dist_json": lead_time_dist_json,
        "lead_time_series_json": lead_time_series_json,
        # Empty defaults for AJAX-loaded tabs
        "client_analysis": {},
        "client_options": [],
        "selected_client": selected_client,
        "client_graphs": {},
        "top10_clients": None,
        "top20_clients": None,
        "concentration_top20_pct": None,
        "concentration_top10_pct": None,
        "client_portfolio": None,
        "client_portfolio_month": None,
        "client_portfolio_quarter": None,
        "client_portfolio_fiscal": None,
        "family_analysis": {},
        "family_analysis_month": {},
        "family_analysis_quarter": {},
        "family_analysis_year": {},
        "family_analysis_fiscal": {},
        "stats_famille": None,
        "family_graphs": {},
        "geo_analysis": _empty_geo,
        "geo_analysis_month": _empty_geo,
        "geo_analysis_quarter": _empty_geo,
        "geo_analysis_fiscal": _empty_geo,
        "stats_pays": [],
        "stats_zone": [],
        "geo_graphs": {},
        "currency_kpi": {},
        "currency_charts": {},
        "currency_kpi_month": {},
        "currency_charts_month": {},
        "currency_kpi_quarter": {},
        "currency_charts_quarter": {},
        "currency_kpi_fiscal": {},
        "currency_charts_fiscal": {},
    }
    return render(request, "client_analytics/stats.html", context)


# ─── AJAX: lazy-load a specific analysis tab ─────────────────────────────────


@require_http_methods(["GET"])
def ajax_tab(request, pk):
    """
    Returns the rendered HTML fragment for a specific analysis tab.
    Called by JavaScript when the user first clicks a non-default tab.

    Query params:
      tab         – one of: temporal | products | clients | geographic | currency
      granularity – month | quarter | year  (default: month)
      client      – (optional) client ID for the clients tab
      product     – (optional) product filter for the products tab
      family      – (optional) family filter for the products tab
    """
    from django.template.loader import render_to_string

    dataset = get_object_or_404(Dataset, pk=pk)
    tab = request.GET.get("tab", "")
    granularity = _normalize_granularity(request.GET.get("granularity", "month"))

    if tab not in ("temporal", "products", "clients", "geographic", "currency"):
        return JsonResponse({"error": f"Unknown tab: {tab!r}"}, status=400)

    df = dataset_io.load_dataset_df(dataset)
    if df is None:
        return JsonResponse({"error": "Dataset load failed"}, status=500)

    try:
        if tab == "temporal":
            ctx = _build_temporal_context(df, granularity=granularity)
            template = "client_analytics/partials/tab_temporal.html"

        elif tab == "products":
            ctx = _build_products_context(
                df,
                granularity=granularity,
                selected_product=request.GET.get("product", ""),
                selected_family=request.GET.get("family", ""),
            )
            template = "client_analytics/partials/tab_products.html"

        elif tab == "clients":
            ctx = _build_clients_context(
                df,
                granularity=granularity,
                selected_client=request.GET.get("client", ""),
            )
            template = "client_analytics/partials/tab_clients.html"

        elif tab == "geographic":
            ctx = _build_geographic_context(df, granularity=granularity)
            template = "client_analytics/partials/tab_geographic.html"

        elif tab == "currency":
            ctx = _build_currency_context(df, granularity=granularity)
            template = "client_analytics/partials/tab_currency.html"

        html = render_to_string(template, ctx, request=request)
        return JsonResponse({"success": True, "html": html})

    except Exception as e:
        logger.exception("[ajax_tab:%s] ERROR", tab)
        return JsonResponse({"error": str(e)}, status=500)


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
            client_col = "Client" if "Client" in df_iforest.columns else None
            if client_col:
                df_iforest = df_iforest[df_iforest[client_col].isin(selected_clients)]
            time_col = (
                "Month" if "Month" in df_iforest.columns else df_iforest.columns[0]
            )
            value_col = (
                "Montant"
                if "Montant" in df_iforest.columns
                else df_iforest.select_dtypes(include="number").columns[0]
            )
            html_iforest, anomalies_df = create_isolation_forest_time_anomaly_plot(
                df_iforest, time_col, value_col, return_anomalies=True
            )
            context["iforest_html"] = html_iforest
            context["iforest_anomalies"] = (
                anomalies_df.to_dict("records") if anomalies_df is not None else []
            )
            context["iforest_time_col"] = time_col
            context["iforest_value_col"] = value_col
        except Exception as e:
            logger.exception("[anomalies] Isolation Forest error")
            context["iforest_html"] = None
            context["iforest_anomalies"] = []
            context["iforest_time_col"] = None
            context["iforest_value_col"] = None

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
