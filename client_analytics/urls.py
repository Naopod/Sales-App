from django.urls import path
from . import views

app_name = "client_analytics"

urlpatterns = [
    path("", views.home, name="home"),
    path("workflow/", views.workflow, name="workflow"),
    path("dataset/<int:pk>/", views.dataset_overview, name="dataset_overview"),
    path("dataset/<int:pk>/stats/", views.stats, name="stats"),
    path("dataset/<int:pk>/anomalies/", views.anomalies, name="anomalies"),
    path("dataset/<int:pk>/clustering/", views.clustering, name="clustering"),
    path(
        "dataset/<int:pk>/clustering/export/",
        views.clustering_export,
        name="clustering_export",
    ),
    # === COPILOT: BEGIN NEW URLS ===
    path(
        "dataset/<int:pk>/ajax/client-portfolio/",
        views.ajax_client_portfolio,
        name="ajax_client_portfolio",
    ),
    path(
        "dataset/<int:pk>/ajax/product-correlation/",
        views.ajax_product_correlation,
        name="ajax_product_correlation",
    ),
    path(
        "dataset/<int:pk>/ajax/compare-products/",
        views.ajax_compare_products,
        name="ajax_compare_products",
    ),
    path(
        "dataset/<int:pk>/ajax/compare-families/",
        views.ajax_compare_families,
        name="ajax_compare_families",
    ),
    # === COPILOT: END NEW URLS ===
]
