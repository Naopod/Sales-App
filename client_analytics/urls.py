from django.urls import path
from . import views

app_name = "client_analytics"

urlpatterns = [
    path("", views.home, name="home"),
    path("workflow/", views.workflow, name="workflow"),
    path("dataset/<int:pk>/", views.dataset_overview, name="dataset_overview"),
    path("dataset/<int:pk>/processing/", views.dataset_processing, name="dataset_processing"),
    path("dataset/<int:pk>/api/start-processing/", views.start_dataset_processing, name="start_dataset_processing"),
    path("dataset/<int:pk>/api/status/", views.check_dataset_status, name="check_dataset_status"),
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
    path(
        "dataset/<int:pk>/ajax/behavioral-client/",
        views.ajax_behavioral_client,
        name="ajax_behavioral_client",
    ),
    path(
        "dataset/<int:pk>/projection/",
        views.projection,
        name="projection",
    ),
    path(
        "dataset/<int:pk>/ajax/projection-client/",
        views.ajax_projection_client,
        name="ajax_projection_client",
    ),
    # === COPILOT: END NEW URLS ===
    path(
        "dataset/<int:pk>/ajax/tab/",
        views.ajax_tab,
        name="ajax_tab",
    ),
    # Chunked upload
    path("api/upload-chunk/", views.upload_chunk, name="upload_chunk"),
    path("api/finalize-upload/", views.finalize_upload, name="finalize_upload"),
]
