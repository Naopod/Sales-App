"""
Service pour l'onglet CLUSTERING
Clustering K-Means automatique avec feature engineering avancé
Adapté du notebook week_1_clean.ipynb
"""
import base64
import os
from io import BytesIO

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import seaborn as sns
from scipy.optimize import linear_sum_assignment

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (
    silhouette_score,
    davies_bouldin_score,
    calinski_harabasz_score,
)
from django.conf import settings

from .visualizations.viz_clustering import (
    create_clustering_pca_plot,
    create_elbow_silhouette_plot,
    create_cluster_distribution_plot,
)

# ─── Constants ────────────────────────────────────────────────────────
TOP_N_FAMILLES = 30
K_RANGE = range(2, 11)
RANDOM_STATE = 42


# ─── Helpers ──────────────────────────────────────────────────────────
def _safe_div(a, b):
    """Division robuste : renvoie 0 si b == 0."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    out = np.zeros_like(a, dtype=float)
    m = b != 0
    out[m] = a[m] / b[m]
    return out


def _open_business_days(start, end):
    """Nombre de jours ouvrés entre deux dates."""
    days = pd.bdate_range(start=start, end=end, freq="B")
    return max(int(len(days)), 1)


# ─── Feature engineering ─────────────────────────────────────────────
def build_client_features(df):
    """
    Construit un DataFrame client-level avec features riches
    (intensités/jour ouvert, logs, ratios, PU Net, CA et parts par famille,
    temps entre commandes, country, diversité).

    Returns
    -------
    (df_client, top_familles)
    """
    df = df.dropna(subset=["Date Cde"]).copy()

    # Top familles par CA
    top_familles = []
    if "Famille" in df.columns:
        top_familles = (
            df.groupby("Famille")["Montant"]
            .sum()
            .sort_values(ascending=False)
            .head(TOP_N_FAMILLES)
            .index.tolist()
        )

    # Jours ouvrés dans la période
    open_days = _open_business_days(df["Date Cde"].min(), df["Date Cde"].max())

    # ── 1) Agrégats client ────────────────────────────────────────────
    agg_dict = {"Montant": ["sum", "mean"], "Quantité": "sum"}
    if "N° Bon" in df.columns:
        agg_dict["N° Bon"] = "nunique"
    if "Delai_Prev_Days" in df.columns:
        agg_dict["Delai_Prev_Days"] = "mean"

    df_client = df.groupby("Cpt Client").agg(agg_dict).reset_index()

    # Flatten multi-index columns
    new_cols = []
    for col in df_client.columns:
        if isinstance(col, tuple):
            new_cols.append("_".join(str(c) for c in col if c).strip("_"))
        else:
            new_cols.append(col)
    df_client.columns = new_cols

    rename_map = {
        "Montant_sum": "CA_Total",
        "Montant_mean": "CA_Moyen",
        "Quantité_sum": "Qty_Total",
    }
    if "N° Bon_nunique" in df_client.columns:
        rename_map["N° Bon_nunique"] = "Nb_Commandes"
    if "Delai_Prev_Days_mean" in df_client.columns:
        rename_map["Delai_Prev_Days_mean"] = "Delai_Moyen"
    df_client = df_client.rename(columns=rename_map)

    if "Nb_Commandes" not in df_client.columns:
        df_client["Nb_Commandes"] = df.groupby("Cpt Client").size().values
    if "Delai_Moyen" not in df_client.columns:
        df_client["Delai_Moyen"] = 0

    # ── 2) Intensités par jour ouvert ─────────────────────────────────
    df_client["CA_par_jour_ouvert"] = df_client["CA_Total"] / open_days
    df_client["Qty_par_jour_ouvert"] = df_client["Qty_Total"] / open_days
    df_client["Cmd_par_jour_ouvert"] = df_client["Nb_Commandes"] / open_days

    # ── 3) Ratios comportementaux ─────────────────────────────────────
    df_client["Panier_moyen"] = _safe_div(
        df_client["CA_Total"].values, df_client["Nb_Commandes"].values
    )
    df_client["Qty_par_commande"] = _safe_div(
        df_client["Qty_Total"].values, df_client["Nb_Commandes"].values
    )
    df_client["CA_par_qty"] = _safe_div(
        df_client["CA_Total"].values, df_client["Qty_Total"].values
    )

    # ── 4) Log transforms ────────────────────────────────────────────
    for col in [
        "CA_par_jour_ouvert",
        "Qty_par_jour_ouvert",
        "Cmd_par_jour_ouvert",
        "CA_Moyen",
        "Panier_moyen",
        "Qty_par_commande",
        "CA_par_qty",
    ]:
        df_client[f"log_{col}"] = np.log1p(
            df_client[col].astype(float).clip(lower=0)
        )

    # ── 5) PU Net moyen par famille ───────────────────────────────────
    if "Famille" in df.columns and "PU Net" in df.columns:
        mat_punet = df.pivot_table(
            index="Cpt Client", columns="Famille", values="PU Net", aggfunc="mean"
        )
        for fam in top_familles:
            if fam in mat_punet.columns:
                col_name = f"PU_Net_{fam}"
                df_client = df_client.merge(
                    mat_punet[[fam]].rename(columns={fam: col_name}),
                    left_on="Cpt Client",
                    right_index=True,
                    how="left",
                )
                df_client[col_name] = df_client[col_name].fillna(0)

    # ── 6) CA par famille + parts de CA ───────────────────────────────
    if "Famille" in df.columns:
        mat_ca = df.pivot_table(
            index="Cpt Client", columns="Famille", values="Montant", aggfunc="sum"
        )
        for fam in top_familles:
            if fam in mat_ca.columns:
                col_name = f"CA_{fam}"
                df_client = df_client.merge(
                    mat_ca[[fam]].rename(columns={fam: col_name}),
                    left_on="Cpt Client",
                    right_index=True,
                    how="left",
                )
                df_client[col_name] = df_client[col_name].fillna(0)
                df_client[f"Part_CA_{fam}"] = _safe_div(
                    df_client[col_name].values, df_client["CA_Total"].values
                )

    # ── 7) Temps entre commandes par famille ──────────────────────────
    if "Famille" in df.columns:
        df_sorted = df.sort_values(["Cpt Client", "Famille", "Date Cde"])
        df_sorted["Date_Suivante"] = df_sorted.groupby(
            ["Cpt Client", "Famille"]
        )["Date Cde"].shift(-1)
        df_sorted["Jours_Entre_Cmd"] = (
            df_sorted["Date_Suivante"] - df_sorted["Date Cde"]
        ).dt.days

        temp = (
            df_sorted.groupby(["Cpt Client", "Famille"])["Jours_Entre_Cmd"]
            .mean()
            .reset_index()
        )
        mat_temps = temp.pivot_table(
            index="Cpt Client",
            columns="Famille",
            values="Jours_Entre_Cmd",
            aggfunc="mean",
        )
        for fam in top_familles:
            if fam in mat_temps.columns:
                col_name = f"Temps_Entre_Cmd_{fam}"
                df_client = df_client.merge(
                    mat_temps[[fam]].rename(columns={fam: col_name}),
                    left_on="Cpt Client",
                    right_index=True,
                    how="left",
                )
                df_client[col_name] = df_client[col_name].fillna(0)

    # ── 8) Country + encoding ─────────────────────────────────────────
    if "Country" in df.columns:
        country_map = df.groupby("Cpt Client")["Country"].first().to_dict()
        df_client["Country"] = (
            df_client["Cpt Client"].map(country_map).fillna("UNKNOWN")
        )
        le = LabelEncoder()
        df_client["Country_Encoded"] = le.fit_transform(
            df_client["Country"].astype(str)
        )
    else:
        df_client["Country"] = "UNKNOWN"
        df_client["Country_Encoded"] = 0

    # ── 9) Diversité produit ──────────────────────────────────────────
    if "Famille" in df.columns:
        nb_fam = df.groupby("Cpt Client")["Famille"].nunique().to_dict()
        df_client["Nb_Familles_Distinctes"] = (
            df_client["Cpt Client"].map(nb_fam).fillna(0)
        )
    else:
        df_client["Nb_Familles_Distinctes"] = 0

    # Fill remaining NaN
    num_cols = df_client.select_dtypes(include=[np.number]).columns
    df_client[num_cols] = df_client[num_cols].fillna(0)

    return df_client, top_familles


def get_features_list(df_client, top_familles):
    """Retourne la liste des features à utiliser pour le clustering."""
    feats = [
        "log_CA_par_jour_ouvert",
        "log_Qty_par_jour_ouvert",
        "log_Cmd_par_jour_ouvert",
        "log_CA_Moyen",
        "log_Panier_moyen",
        "log_Qty_par_commande",
        "log_CA_par_qty",
        "Country_Encoded",
        "Nb_Familles_Distinctes",
        "Delai_Moyen",
    ]
    for fam in top_familles:
        feats.append(f"PU_Net_{fam}")
    for fam in top_familles:
        feats.append(f"Part_CA_{fam}")
    for fam in top_familles:
        feats.append(f"Temps_Entre_Cmd_{fam}")

    return [f for f in feats if f in df_client.columns]


# ─── Optimal K selection ─────────────────────────────────────────────
def find_optimal_k(X_scaled):
    """Teste K=2..10, retourne le K optimal (silhouette) et les métriques."""
    results = []
    for k in K_RANGE:
        if X_scaled.shape[0] <= k:
            break
        km = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=10, max_iter=300)
        labels = km.fit_predict(X_scaled)
        if len(np.unique(labels)) < 2:
            continue
        results.append(
            {
                "k": k,
                "inertia": float(km.inertia_),
                "silhouette": float(silhouette_score(X_scaled, labels)),
                "davies_bouldin": float(davies_bouldin_score(X_scaled, labels)),
                "calinski_harabasz": float(
                    calinski_harabasz_score(X_scaled, labels)
                ),
            }
        )

    if not results:
        return {"optimal_k": 2, "metrics": []}

    best = max(results, key=lambda r: r["silhouette"])
    return {"optimal_k": best["k"], "metrics": results}


# ─── Cluster profiling ───────────────────────────────────────────────
def build_cluster_profiles(df_client, top_familles, n_clusters):
    """Construit le profil détaillé de chaque cluster."""
    profiles = []
    ca_fam_cols = [
        f"CA_{fam}" for fam in top_familles if f"CA_{fam}" in df_client.columns
    ]

    for cluster_id in range(n_clusters):
        cluster_data = df_client[df_client["Cluster"] == cluster_id]
        n = len(cluster_data)
        if n == 0:
            continue

        profile = {
            "id": cluster_id,
            "nb_clients": n,
            "pct": round(n / len(df_client) * 100, 1),
            "ca_total_moyen": round(float(cluster_data["CA_Total"].mean()), 2),
            "ca_total_sum": round(float(cluster_data["CA_Total"].sum()), 2),
            "qty_total_moyen": round(float(cluster_data["Qty_Total"].mean()), 2),
            "nb_commandes_moyen": round(
                float(cluster_data["Nb_Commandes"].mean()), 1
            ),
            "panier_moyen": round(
                float(cluster_data["Panier_moyen"].mean()), 2
            ),
            "delai_moyen": round(
                float(cluster_data["Delai_Moyen"].mean()), 1
            ),
            "nb_familles_moyen": round(
                float(cluster_data["Nb_Familles_Distinctes"].mean()), 1
            ),
        }

        # Top 5 familles par CA moyen
        if ca_fam_cols:
            fam_ca = {}
            for col in ca_fam_cols:
                fam_name = col.replace("CA_", "")
                ca_mean = float(cluster_data[col].mean())
                if ca_mean > 0:
                    fam_ca[fam_name] = round(ca_mean, 2)
            top_fam = sorted(fam_ca.items(), key=lambda x: x[1], reverse=True)[
                :5
            ]
            profile["top_familles"] = [
                {"nom": f, "ca_moyen": v} for f, v in top_fam
            ]
        else:
            profile["top_familles"] = []

        # Top 3 pays
        if "Country" in cluster_data.columns:
            top_pays = cluster_data["Country"].value_counts().head(3)
            profile["top_pays"] = [
                {
                    "pays": pays,
                    "count": int(count),
                    "pct": round(count / n * 100, 1),
                }
                for pays, count in top_pays.items()
            ]
        else:
            profile["top_pays"] = []

        profiles.append(profile)

    return profiles


# ─── Main entry point ────────────────────────────────────────────────
def generate_clustering_analysis(df):
    """
    Génère l'analyse de clustering complète automatique.

    Args:
        df: DataFrame des transactions brutes (post-processing)

    Returns:
        dict avec 'results', 'graphs', 'kpis'
    """
    try:
        if df is None or df.empty:
            return {
                "results": {},
                "graphs": {},
                "kpis": {},
                "error": "Aucune donnee disponible pour lancer le clustering.",
            }

        # 1) Feature engineering
        df_client, top_familles = build_client_features(df)
        if len(df_client) < 3:
            return {
                "results": {},
                "graphs": {},
                "kpis": {},
                "error": (
                    "Le clustering requiert au moins 3 clients distincts "
                    "sur le perimetre analyse."
                ),
            }

        features = get_features_list(df_client, top_familles)

        if len(features) < 2:
            return {
                "results": {},
                "graphs": {},
                "kpis": {},
                "error": "Pas assez de features pour le clustering",
            }

        X = df_client[features].fillna(0)

        # 2) Scaling
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # 3) Optimal K
        k_result = find_optimal_k(X_scaled)
        optimal_k = k_result["optimal_k"]

        # 4) Final clustering
        kmeans = KMeans(
            n_clusters=optimal_k, random_state=RANDOM_STATE, n_init=20, max_iter=500
        )
        df_client["Cluster"] = kmeans.fit_predict(X_scaled)

        sil = float(silhouette_score(X_scaled, df_client["Cluster"]))
        db = float(davies_bouldin_score(X_scaled, df_client["Cluster"]))
        ch = float(calinski_harabasz_score(X_scaled, df_client["Cluster"]))

        # 5) Profiles
        profiles = build_cluster_profiles(df_client, top_familles, optimal_k)

        # 6) Graphs
        graphs = {}
        pca_plot = create_clustering_pca_plot(df_client, X_scaled)
        if pca_plot:
            graphs["clustering_pca"] = pca_plot

        elbow_plot = create_elbow_silhouette_plot(k_result["metrics"], optimal_k)
        if elbow_plot:
            graphs["elbow_silhouette"] = elbow_plot

        distrib_plot = create_cluster_distribution_plot(profiles)
        if distrib_plot:
            graphs["cluster_distribution"] = distrib_plot

        # 7) Pack results
        kpis = {
            "nb_clusters": optimal_k,
            "silhouette_score": round(sil, 4),
            "davies_bouldin_score": round(db, 4),
            "calinski_harabasz_score": round(ch, 2),
            "nb_clients": len(df_client),
            "nb_features": len(features),
            "inertia": round(float(kmeans.inertia_), 2),
        }

        results = {
            "profiles": profiles,
            "k_metrics": k_result["metrics"],
            "features_used": features,
            "top_familles": top_familles,
        }

        return {"results": results, "graphs": graphs, "kpis": kpis}

    except Exception as e:
        return {"results": {}, "graphs": {}, "kpis": {}, "error": str(e)}


def get_quarterly_clustering_available_years(df):
    """Liste les annees calendaires disponibles pour le clustering notebook."""
    if df is None or df.empty or "Date Cde" not in df.columns:
        return []

    date_series = df["Date Cde"]
    if not np.issubdtype(date_series.dtype, np.datetime64):
        date_series = pd.to_datetime(date_series, errors="coerce")

    return sorted(date_series.dt.year.dropna().astype(int).unique().tolist())


def get_notebook_closed_periods_by_year():
    """Retourne la configuration des periodes fermees definie dans settings."""
    return getattr(
        settings,
        "CLUSTERING_NOTEBOOK_CLOSED_PERIODS_BY_YEAR",
        {2024: [("2024-08-01", "2024-08-26")]},
    )


def generate_quarterly_clustering_analysis(df, year=None):
    """
    Portage fidele de la cellule "CLUSTERING TRIMESTRIEL 2024 + VACANCES"
    du notebook week_1_clean.ipynb, rendu parametrable par annee.
    """
    RANDOM_STATE = 42
    K_RANGE = range(2, 11)

    def quarter_start_end(quarter_str: str):
        p = pd.Period(quarter_str, freq="Q")
        return p.start_time.normalize(), p.end_time.normalize()

    def open_business_days_in_quarter(quarter_str: str, closed_periods=None) -> int:
        start, end = quarter_start_end(quarter_str)
        days = pd.bdate_range(start=start, end=end, freq="B")
        if closed_periods:
            mask = pd.Series(False, index=days)
            for cstart, cend in closed_periods:
                cstart = pd.Timestamp(cstart)
                cend = pd.Timestamp(cend)
                mask |= (days >= cstart) & (days <= cend)
            days = days[~mask.values]
        return int(len(days))

    def safe_div(a, b):
        a = np.asarray(a, dtype=float)
        b = np.asarray(b, dtype=float)
        out = np.zeros_like(a, dtype=float)
        m = b != 0
        out[m] = a[m] / b[m]
        return out

    def align_labels_by_centroids(
        centroids_ref: np.ndarray,
        centroids_new: np.ndarray,
        labels_new: np.ndarray,
    ) -> np.ndarray:
        dists = np.linalg.norm(
            centroids_ref[:, None, :] - centroids_new[None, :, :], axis=2
        )
        row_ind, col_ind = linear_sum_assignment(dists)
        mapping = {new: ref for ref, new in zip(row_ind, col_ind)}
        aligned = np.vectorize(lambda x: mapping.get(x, x))(labels_new)
        return aligned

    def build_client_features_for_quarter(
        df_trim: pd.DataFrame, top_familles: list, open_days: int
    ) -> pd.DataFrame:
        df_trim = df_trim.dropna(subset=["Date Cde"]).copy()
        open_days = max(int(open_days), 1)

        df_client = df_trim.groupby("Cpt Client").agg(
            CA_Total=("Montant", "sum"),
            CA_Moyen=("Montant", "mean"),
            Qty_Total=("Quantité", "sum"),
            Delai_Moyen=("Delai_Prev_Days", "mean"),
            Nb_Commandes=("N° Bon", "nunique"),
        ).reset_index()

        df_client["CA_par_jour_ouvert"] = df_client["CA_Total"] / open_days
        df_client["Qty_par_jour_ouvert"] = df_client["Qty_Total"] / open_days
        df_client["Cmd_par_jour_ouvert"] = df_client["Nb_Commandes"] / open_days

        df_client["Panier_moyen"] = safe_div(
            df_client["CA_Total"], df_client["Nb_Commandes"]
        )
        df_client["Qty_par_commande"] = safe_div(
            df_client["Qty_Total"], df_client["Nb_Commandes"]
        )
        df_client["CA_par_qty"] = safe_div(
            df_client["CA_Total"], df_client["Qty_Total"]
        )

        for col in [
            "CA_par_jour_ouvert",
            "Qty_par_jour_ouvert",
            "Cmd_par_jour_ouvert",
            "CA_Moyen",
            "Panier_moyen",
            "Qty_par_commande",
            "CA_par_qty",
        ]:
            df_client[f"log_{col}"] = np.log1p(
                df_client[col].astype(float).clip(lower=0)
            )

        mat_punet = df_trim.pivot_table(
            index="Cpt Client", columns="Famille", values="PU Net", aggfunc="mean"
        )
        for fam in top_familles:
            if fam in mat_punet.columns:
                col = f"PU_Net_{fam}"
                df_client = df_client.merge(
                    mat_punet[[fam]].rename(columns={fam: col}),
                    left_on="Cpt Client",
                    right_index=True,
                    how="left",
                )
                df_client[col] = df_client[col].fillna(0)

        df_trim["CA_Famille"] = df_trim["Montant"]
        mat_ca = df_trim.pivot_table(
            index="Cpt Client",
            columns="Famille",
            values="CA_Famille",
            aggfunc="sum",
        )
        for fam in top_familles:
            if fam in mat_ca.columns:
                col = f"CA_{fam}"
                df_client = df_client.merge(
                    mat_ca[[fam]].rename(columns={fam: col}),
                    left_on="Cpt Client",
                    right_index=True,
                    how="left",
                )
                df_client[col] = df_client[col].fillna(0)
                df_client[f"Part_CA_{fam}"] = safe_div(
                    df_client[col], df_client["CA_Total"]
                )

        df_sorted = df_trim.sort_values(["Cpt Client", "Famille", "Date Cde"])
        df_sorted["Date_Suivante"] = df_sorted.groupby(
            ["Cpt Client", "Famille"]
        )["Date Cde"].shift(-1)
        df_sorted["Jours_Entre_Cmd"] = (
            df_sorted["Date_Suivante"] - df_sorted["Date Cde"]
        ).dt.days

        temp = (
            df_sorted.groupby(["Cpt Client", "Famille"])["Jours_Entre_Cmd"]
            .mean()
            .reset_index()
        )
        mat_temps = temp.pivot_table(
            index="Cpt Client",
            columns="Famille",
            values="Jours_Entre_Cmd",
            aggfunc="mean",
        )
        for fam in top_familles:
            if fam in mat_temps.columns:
                col = f"Temps_Entre_Cmd_{fam}"
                df_client = df_client.merge(
                    mat_temps[[fam]].rename(columns={fam: col}),
                    left_on="Cpt Client",
                    right_index=True,
                    how="left",
                )
                df_client[col] = df_client[col].fillna(0)

        country_map = df_trim.groupby("Cpt Client")["Country"].first().to_dict()
        df_client["Country"] = (
            df_client["Cpt Client"].map(country_map).fillna("UNKNOWN")
        )

        nb_fam = df_trim.groupby("Cpt Client")["Famille"].nunique().to_dict()
        df_client["Nb_Familles_Distinctes"] = (
            df_client["Cpt Client"].map(nb_fam).fillna(0)
        )

        return df_client

    def get_quarter_features_list(df_client: pd.DataFrame, top_familles: list) -> list:
        feats = [
            "log_CA_par_jour_ouvert",
            "log_Qty_par_jour_ouvert",
            "log_Cmd_par_jour_ouvert",
            "log_CA_Moyen",
            "log_Panier_moyen",
            "log_Qty_par_commande",
            "log_CA_par_qty",
            "Country_Encoded",
            "Nb_Familles_Distinctes",
            "Delai_Moyen",
        ]
        for fam in top_familles:
            feats.append(f"PU_Net_{fam}")
        for fam in top_familles:
            feats.append(f"Part_CA_{fam}")
        for fam in top_familles:
            feats.append(f"Temps_Entre_Cmd_{fam}")
        return [f for f in feats if f in df_client.columns]

    try:
        df_final = df.copy()
        available_years = get_quarterly_clustering_available_years(df_final)

        if "Date Cde" not in df_final.columns:
            return {
                "results": {},
                "graphs": {},
                "kpis": {},
                "error": "Le clustering trimestriel du notebook requiert la colonne 'Date Cde'.",
            }

        if not np.issubdtype(df_final["Date Cde"].dtype, np.datetime64):
            df_final["Date Cde"] = pd.to_datetime(df_final["Date Cde"], errors="coerce")

        if year is None:
            selected_year = available_years[-1] if available_years else None
        else:
            try:
                selected_year = int(year)
            except (TypeError, ValueError):
                return {
                    "results": {},
                    "graphs": {},
                    "kpis": {},
                    "error": "L'annee selectionnee est invalide pour le clustering trimestriel.",
                }

        if selected_year is None:
            return {
                "results": {},
                "graphs": {},
                "kpis": {},
                "error": "Aucune date exploitable n'est disponible pour le clustering trimestriel.",
            }

        # Le notebook source travaille avec un Quarter calendaire (to_period("Q")).
        df_final["Quarter"] = df_final["Date Cde"].dt.to_period("Q").astype(str)

        df_final = df_final.dropna(subset=["Date Cde"])
        df_year = df_final[
            df_final["Quarter"].astype(str).str.startswith(f"{selected_year}", na=False)
        ].copy()
        closed_periods = get_notebook_closed_periods_by_year().get(selected_year, [])

        if df_year.empty:
            return {
                "results": {},
                "graphs": {},
                "kpis": {},
                "error": (
                    f"Aucune donnee {selected_year} disponible pour executer le "
                    "clustering trimestriel du notebook."
                ),
            }

        trimestres = sorted(df_year["Quarter"].unique())
        top_familles = (
            df_year.groupby("Famille")["Montant"]
            .sum()
            .sort_values(ascending=False)
            .head(TOP_N_FAMILLES)
            .index.tolist()
        )
        all_clients = sorted(df_year["Cpt Client"].unique())
        country_global = df_year.groupby("Cpt Client")["Country"].first().to_dict()

        client_dfs = {}
        feature_lists = {}
        quarterly_summaries = []

        for trim in trimestres:
            df_trim = df_year[df_year["Quarter"] == trim].copy()
            open_days = open_business_days_in_quarter(trim, closed_periods)

            df_client_active = build_client_features_for_quarter(
                df_trim, top_familles, open_days
            )
            df_client_active["Trimestre"] = trim

            base = pd.DataFrame({"Cpt Client": all_clients, "Trimestre": trim})
            df_client = base.merge(
                df_client_active, on=["Cpt Client", "Trimestre"], how="left"
            )

            df_client["Nb_Commandes"] = df_client["Nb_Commandes"].fillna(0)
            df_client["is_active"] = (df_client["Nb_Commandes"] > 0).astype(int)

            num_cols = df_client.select_dtypes(include=[np.number]).columns
            df_client[num_cols] = df_client[num_cols].fillna(0)

            df_client["Country"] = (
                df_client["Country"]
                .fillna(df_client["Cpt Client"].map(country_global))
                .fillna("UNKNOWN")
            )

            client_dfs[trim] = df_client
            quarterly_summaries.append(
                {
                    "trimestre": trim,
                    "transactions": int(len(df_trim)),
                    "jours_ouverts": int(max(open_days, 1)),
                    "nb_clients_total": int(len(df_client)),
                    "nb_clients_actifs": int(df_client["is_active"].sum()),
                }
            )

        all_countries = pd.concat(
            [client_dfs[t]["Country"] for t in trimestres], axis=0
        ).astype(str).fillna("UNKNOWN")
        le_country = LabelEncoder().fit(all_countries)

        for trim in trimestres:
            client_dfs[trim]["Country_Encoded"] = le_country.transform(
                client_dfs[trim]["Country"].astype(str).fillna("UNKNOWN")
            )

        for trim in trimestres:
            feature_lists[trim] = get_quarter_features_list(
                client_dfs[trim], top_familles
            )

        all_feats = sorted({f for trim in trimestres for f in feature_lists[trim]})
        active_rows = []
        for trim in trimestres:
            df_c = client_dfs[trim].copy()
            df_a = df_c[df_c["is_active"] == 1].copy().fillna(0)

            for f in all_feats:
                if f not in df_a.columns:
                    df_a[f] = 0

            active_rows.append(df_a[all_feats])

        panel_active = pd.concat(active_rows, ignore_index=True).fillna(0)
        if panel_active.empty:
            return {
                "results": {},
                "graphs": {},
                "kpis": {},
                "error": "Aucun client actif trouve pour le clustering trimestriel.",
            }

        scaler_global = StandardScaler().fit(panel_active)

        k_scores = {}
        for k in K_RANGE:
            scores = []
            ok = True

            for trim in trimestres:
                df_c = client_dfs[trim].copy()
                df_c = df_c[df_c["is_active"] == 1].copy().fillna(0)

                for f in all_feats:
                    if f not in df_c.columns:
                        df_c[f] = 0

                X_scaled = scaler_global.transform(df_c[all_feats])

                if X_scaled.shape[0] <= k:
                    ok = False
                    break

                km_tmp = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=10)
                labels_tmp = km_tmp.fit_predict(X_scaled)

                if len(np.unique(labels_tmp)) < 2:
                    ok = False
                    break

                sil = silhouette_score(X_scaled, labels_tmp)
                scores.append(sil)

            if ok and len(scores) > 0:
                k_scores[k] = float(np.mean(scores))

        if len(k_scores) == 0:
            return {
                "results": {},
                "graphs": {},
                "kpis": {},
                "error": (
                    "Impossible de calculer la silhouette "
                    "(trop peu de clients ou donnees problematiques)."
                ),
            }

        K_FIXED = max(k_scores, key=k_scores.get)

        clusters_par_trimestre = {}
        centroids_par_trimestre = {}
        distributions = []

        for idx, trim in enumerate(trimestres):
            df_c = client_dfs[trim].copy()

            active_mask = df_c["is_active"] == 1
            df_active = df_c[active_mask].copy().fillna(0)

            for f in all_feats:
                if f not in df_active.columns:
                    df_active[f] = 0

            X_scaled = scaler_global.transform(df_active[all_feats])

            km = KMeans(n_clusters=K_FIXED, random_state=RANDOM_STATE, n_init=10)
            labels = km.fit_predict(X_scaled)
            centroids = km.cluster_centers_

            if idx == 0:
                labels_aligned = labels
                centroids_ref = centroids
            else:
                labels_aligned = align_labels_by_centroids(
                    centroids_ref, centroids, labels
                )

                dists = np.linalg.norm(
                    centroids_ref[:, None, :] - centroids[None, :, :], axis=2
                )
                row_ind, col_ind = linear_sum_assignment(dists)
                centroids_aligned = np.zeros_like(centroids_ref)
                for k_ref, k_new in zip(row_ind, col_ind):
                    centroids_aligned[k_ref] = centroids[k_new]
                centroids = centroids_aligned

            df_c["Cluster"] = -1
            df_c.loc[active_mask, "Cluster"] = labels_aligned

            clusters_par_trimestre[trim] = df_c[
                ["Cpt Client", "Trimestre", "is_active", "Cluster"]
            ].copy()
            centroids_par_trimestre[trim] = centroids

            dist = df_c["Cluster"].value_counts().sort_index()
            rows = []
            for c, n in dist.items():
                rows.append(
                    {
                        "cluster": "INACTIF (-1)" if c == -1 else f"Cluster {c}",
                        "nb_clients": int(n),
                        "pct": round(n / len(df_c) * 100, 1),
                    }
                )
            dist_df = pd.DataFrame(rows)
            distributions.append(
                {
                    "trimestre": trim,
                    "table_html": dist_df.to_html(
                        index=False,
                        classes="table table-striped table-sm",
                        border=0,
                    ),
                }
            )

        KPIS = [
            "CA_par_jour_ouvert",
            "Cmd_par_jour_ouvert",
            "Panier_moyen",
            "Nb_Familles_Distinctes",
        ]
        comparisons = []

        for trim in trimestres:
            tmp = client_dfs[trim].merge(
                clusters_par_trimestre[trim][["Cpt Client", "Cluster"]],
                on="Cpt Client",
                how="left",
            )

            g = tmp.groupby("Cluster")[KPIS].mean()
            if -1 in g.index:
                g = g.drop(index=-1)

            if not set([0, 1]).issubset(set(g.index)):
                comparisons.append(
                    {
                        "trimestre": trim,
                        "table_html": None,
                        "message": (
                            f"Clusters 0/1 non disponibles "
                            f"(clusters presents: {list(g.index)})"
                        ),
                    }
                )
                continue

            c0 = g.loc[0]
            c1 = g.loc[1]
            rows = []
            for kpi in KPIS:
                v0, v1 = float(c0[kpi]), float(c1[kpi])
                rows.append(
                    {
                        "kpi": kpi,
                        "cluster_0": round(v0, 2),
                        "cluster_1": round(v1, 2),
                        "gagne": "Cluster 0" if v0 >= v1 else "Cluster 1",
                    }
                )
            comp_df = pd.DataFrame(rows)
            comparisons.append(
                {
                    "trimestre": trim,
                    "table_html": comp_df.to_html(
                        index=False,
                        classes="table table-striped table-sm",
                        border=0,
                    ),
                    "message": None,
                }
            )

        df_pivot = pd.DataFrame()
        for trim in trimestres:
            tmp = clusters_par_trimestre[trim][["Cpt Client", "Cluster"]].rename(
                columns={"Cluster": f"Q{trim}"}
            )
            df_pivot = tmp if df_pivot.empty else df_pivot.merge(
                tmp, on="Cpt Client", how="outer"
            )

        df_pivot = df_pivot.set_index("Cpt Client")

        matrices_transition = {}
        transition_tables = []
        for i in range(len(trimestres) - 1):
            t0, t1 = trimestres[i], trimestres[i + 1]
            col0, col1 = f"Q{t0}", f"Q{t1}"

            df_tr = df_pivot[[col0, col1]].dropna()
            n = len(df_tr)
            if n == 0:
                continue

            eff = pd.crosstab(df_tr[col0], df_tr[col1])
            pct = pd.crosstab(df_tr[col0], df_tr[col1], normalize="index") * 100
            stables = int((df_tr[col0] == df_tr[col1]).sum())
            migrants = int(n - stables)

            key = f"{t0}_{t1}"
            matrices_transition[key] = {
                "effectifs": eff,
                "pourcentages": pct,
                "nb_clients": int(n),
                "stables": stables,
                "migrants": migrants,
            }
            transition_tables.append(
                {
                    "label": f"{t0} -> {t1}",
                    "nb_clients": int(n),
                    "stables": stables,
                    "migrants": migrants,
                    "effectifs_html": eff.to_html(
                        classes="table table-striped table-sm", border=0
                    ),
                    "pourcentages_html": pct.round(1).to_html(
                        classes="table table-striped table-sm", border=0
                    ),
                }
            )

        transition_heatmap = None
        nb = len(matrices_transition)
        if nb > 0:
            fig, axes = plt.subplots(1, nb, figsize=(8 * nb, 6))
            if nb == 1:
                axes = [axes]

            for ax, (key, data) in zip(axes, matrices_transition.items()):
                sns.heatmap(
                    data["pourcentages"],
                    annot=True,
                    fmt=".1f",
                    vmin=0,
                    vmax=100,
                    ax=ax,
                )
                ax.set_title(f"Transition {key}\n({data['nb_clients']} clients)")
                ax.set_xlabel("Vers (trimestre suivant)")
                ax.set_ylabel("De (trimestre actuel)")

            plt.tight_layout()
            buffer = BytesIO()
            fig.savefig(buffer, format="png", bbox_inches="tight", dpi=150)
            buffer.seek(0)
            transition_heatmap = base64.b64encode(buffer.read()).decode("utf-8")
            plt.close(fig)

        k_scores_rows = [
            {"k": int(k), "silhouette_moyenne": round(v, 4)}
            for k, v in sorted(k_scores.items())
        ]
        k_scores_df = pd.DataFrame(k_scores_rows)

        results = {
            "selected_year": int(selected_year),
            "available_years": available_years,
            "trimestres": trimestres,
            "closed_periods": closed_periods,
            "top_familles": top_familles,
            "quarterly_summaries": quarterly_summaries,
            "k_scores_html": k_scores_df.to_html(
                index=False,
                classes="table table-striped table-sm",
                border=0,
            ),
            "quarter_distributions": distributions,
            "comparisons": comparisons,
            "transition_tables": transition_tables,
        }
        graphs = {"transition_heatmap": transition_heatmap}
        kpis = {
            "annee_analysee": int(selected_year),
            "k_fixed": int(K_FIXED),
            "silhouette_moyenne": round(float(k_scores[K_FIXED]), 4),
            "nb_trimestres": int(len(trimestres)),
            "nb_clients": int(len(all_clients)),
            "nb_top_familles": int(len(top_familles)),
        }

        return {"results": results, "graphs": graphs, "kpis": kpis}

    except Exception as e:
        return {"results": {}, "graphs": {}, "kpis": {}, "error": str(e)}


def generate_clustering_tab_analysis(df):
    """Alias pour compatibilité."""
    return generate_clustering_analysis(df)


# ═══════════════════════════════════════════════════════════════════════
# Sales clustering: business-first static and temporal clustering
# ═══════════════════════════════════════════════════════════════════════

_PERIOD_COLUMNS = {
    "month": "Month",
    "quarter": "Fiscal_Quarter",
    "year": "Fiscal_Year_Label",
}

_GRANULARITY_LABELS = {
    "month": "Mois",
    "quarter": "Trimestre",
    "year": "Année fiscale",
}


def _to_html(fig) -> str:
    fig.update_layout(
        autosize=True,
        width=None,
        margin=dict(l=24, r=20, t=58, b=32),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=12),
    )
    return fig.to_html(full_html=False, include_plotlyjs=False, config={"responsive": True})


def _period_col(granularity: str) -> str:
    return _PERIOD_COLUMNS.get(granularity, "Month")


def _product_entity_col(df: pd.DataFrame) -> tuple[str | None, str]:
    candidates = [
        "Code Recette",
        "Code Produit",
        "Produit",
        "Article",
        "Libelle 1",
        "Libellé 1",
        "Désignation",
        "Designation",
        "Famille",
    ]
    for col in candidates:
        if col in df.columns:
            label = "Famille produit" if col == "Famille" else "Produit"
            return col, label
    return None, "Produit"


def _sorted_period_values(values, granularity: str) -> list[str]:
    vals = [str(v) for v in values if pd.notna(v) and str(v)]
    if granularity == "month":
        return sorted(vals)
    if granularity == "year":
        return sorted(vals, key=lambda x: int(str(x).replace("FY", "")) if str(x).replace("FY", "").isdigit() else 0)
    if granularity == "quarter":
        def key(v: str):
            s = str(v)
            fy = 0
            q = 0
            if "FY" in s:
                try:
                    fy = int(s.split("FY")[-1].strip())
                except Exception:
                    fy = 0
            if s.startswith("Q") and len(s) > 1 and s[1].isdigit():
                q = int(s[1])
            return (fy, q, s)
        return sorted(vals, key=key)
    return sorted(vals)


def get_sales_clustering_period_options(df: pd.DataFrame) -> dict:
    options = {}
    if df is None or df.empty:
        return {"month": [], "quarter": [], "year": []}
    for granularity, col in _PERIOD_COLUMNS.items():
        if col in df.columns:
            options[granularity] = _sorted_period_values(df[col].dropna().unique(), granularity)
        else:
            options[granularity] = []
    return options


def _filter_period(df: pd.DataFrame, granularity: str, period: str | None) -> pd.DataFrame:
    col = _period_col(granularity)
    if not period or period == "all" or col not in df.columns:
        return df.copy()
    return df[df[col].astype(str) == str(period)].copy()


def _filter_period_range(
    df: pd.DataFrame,
    granularity: str,
    period_start: str | None,
    period_end: str | None,
) -> pd.DataFrame:
    col = _period_col(granularity)
    if col not in df.columns:
        return df.copy()
    periods = _sorted_period_values(df[col].dropna().unique(), granularity)
    if not periods:
        return df.copy()
    start = period_start if period_start in periods else periods[0]
    end = period_end if period_end in periods else periods[-1]
    start_idx = periods.index(start)
    end_idx = periods.index(end)
    if start_idx > end_idx:
        start_idx, end_idx = end_idx, start_idx
    keep = set(periods[start_idx:end_idx + 1])
    return df[df[col].astype(str).isin(keep)].copy()


def _order_period_bounds(available: list[str], start: str | None, end: str | None) -> tuple[str | None, str | None]:
    if start in available and end in available and available.index(start) > available.index(end):
        return end, start
    return start, end


def _money(value) -> str:
    try:
        return f"{float(value):,.0f} €".replace(",", " ")
    except Exception:
        return "0 €"


def _clean_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return out


def _build_client_sales_features(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str], str]:
    if "Cpt Client" not in df.columns:
        return pd.DataFrame(), [], "Colonne client manquante"
    if "Montant" not in df.columns:
        return pd.DataFrame(), [], "Colonne montant manquante"

    base = df.copy()
    base["Montant"] = pd.to_numeric(base.get("Montant"), errors="coerce")
    base["Quantité"] = pd.to_numeric(base.get("Quantité"), errors="coerce") if "Quantité" in base.columns else 0
    if "PU Net" in base.columns:
        base["PU Net"] = pd.to_numeric(base.get("PU Net"), errors="coerce")
    if "Lead_Time_Days" in base.columns:
        base["Lead_Time_Days"] = pd.to_numeric(base.get("Lead_Time_Days"), errors="coerce")
    if "Lead_Time_Deviation_Days" in base.columns:
        base["Lead_Time_Deviation_Days"] = pd.to_numeric(base.get("Lead_Time_Deviation_Days"), errors="coerce")

    agg = {
        "Montant": ["sum", "mean"],
        "Quantité": "sum",
    }
    if "N° Bon" in base.columns:
        agg["N° Bon"] = pd.Series.nunique
    if "Famille" in base.columns:
        agg["Famille"] = pd.Series.nunique
    if "Country" in base.columns:
        agg["Country"] = pd.Series.nunique
    if "PU Net" in base.columns:
        agg["PU Net"] = "mean"
    if "Lead_Time_Days" in base.columns:
        agg["Lead_Time_Days"] = "median"
    if "Lead_Time_Deviation_Days" in base.columns:
        agg["Lead_Time_Deviation_Days"] = "mean"

    features = base.groupby("Cpt Client").agg(agg)
    features.columns = ["_".join([str(x) for x in col if x]).strip("_") for col in features.columns]
    features = features.reset_index().rename(columns={
        "Cpt Client": "Entity",
        "Montant_sum": "CA_Total",
        "Montant_mean": "CA_Moyen",
        "Quantité_sum": "Qty_Total",
        "N° Bon_nunique": "Nb_Commandes",
        "Famille_nunique": "Nb_Familles",
        "Country_nunique": "Nb_Pays",
        "PU Net_mean": "PU_Moyen",
        "Lead_Time_Days_median": "Lead_Time_Median",
        "Lead_Time_Deviation_Days_mean": "Retard_Moyen",
    })
    if "Nb_Commandes" not in features.columns:
        features["Nb_Commandes"] = base.groupby("Cpt Client").size().values
    for col in ["Nb_Familles", "Nb_Pays", "PU_Moyen", "Lead_Time_Median", "Retard_Moyen"]:
        if col not in features.columns:
            features[col] = 0

    features["Panier_Moyen"] = _safe_div(features["CA_Total"].values, features["Nb_Commandes"].values)
    features["Qty_Par_Commande"] = _safe_div(features["Qty_Total"].values, features["Nb_Commandes"].values)

    if "Nom Devise" in base.columns:
        total = base.groupby("Cpt Client")["Montant"].sum()
        non_eur = base[base["Nom Devise"].astype(str).str.upper() != "EUR"].groupby("Cpt Client")["Montant"].sum()
        features["Part_Non_EUR"] = features["Entity"].map(((non_eur / total) * 100).fillna(0)).fillna(0)
    else:
        features["Part_Non_EUR"] = 0

    if "Country" in base.columns:
        features["Segment_Detail"] = features["Entity"].map(base.groupby("Cpt Client")["Country"].agg(lambda x: x.mode().iloc[0] if not x.mode().empty else "N/A")).fillna("N/A")
    else:
        features["Segment_Detail"] = ""

    feature_cols = [
        "CA_Total", "CA_Moyen", "Qty_Total", "Nb_Commandes", "Nb_Familles",
        "Nb_Pays", "Panier_Moyen", "Qty_Par_Commande", "PU_Moyen",
        "Lead_Time_Median", "Retard_Moyen", "Part_Non_EUR",
    ]
    features = _clean_numeric(features, feature_cols)
    return features, feature_cols, ""


def _build_product_sales_features(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str], str, str]:
    entity_col, entity_label = _product_entity_col(df)
    if not entity_col:
        return pd.DataFrame(), [], "Aucune colonne produit exploitable", entity_label
    if "Montant" not in df.columns:
        return pd.DataFrame(), [], "Colonne montant manquante", entity_label

    base = df.copy()
    base[entity_col] = base[entity_col].astype(str)
    base["Montant"] = pd.to_numeric(base.get("Montant"), errors="coerce")
    base["Quantité"] = pd.to_numeric(base.get("Quantité"), errors="coerce") if "Quantité" in base.columns else 0
    if "PU Net" in base.columns:
        base["PU Net"] = pd.to_numeric(base.get("PU Net"), errors="coerce")
    if "Lead_Time_Days" in base.columns:
        base["Lead_Time_Days"] = pd.to_numeric(base.get("Lead_Time_Days"), errors="coerce")

    agg = {
        "Montant": "sum",
        "Quantité": "sum",
    }
    if "N° Bon" in base.columns:
        agg["N° Bon"] = pd.Series.nunique
    if "Cpt Client" in base.columns:
        agg["Cpt Client"] = pd.Series.nunique
    if "Country" in base.columns:
        agg["Country"] = pd.Series.nunique
    if "PU Net" in base.columns:
        agg["PU Net"] = "mean"
    if "Lead_Time_Days" in base.columns:
        agg["Lead_Time_Days"] = "median"

    features = base.groupby(entity_col).agg(agg)
    features = features.reset_index().rename(columns={
        entity_col: "Entity",
        "Montant": "CA_Total",
        "Quantité": "Qty_Total",
        "N° Bon": "Nb_Commandes",
        "Cpt Client": "Nb_Clients",
        "Country": "Nb_Pays",
        "PU Net": "PU_Moyen",
        "Lead_Time_Days": "Lead_Time_Median",
    })
    if "Nb_Commandes" not in features.columns:
        features["Nb_Commandes"] = base.groupby(entity_col).size().values
    for col in ["Nb_Clients", "Nb_Pays", "PU_Moyen", "Lead_Time_Median"]:
        if col not in features.columns:
            features[col] = 0
    features["PU_Pondere"] = _safe_div(features["CA_Total"].values, features["Qty_Total"].values)
    features["CA_Par_Client"] = _safe_div(features["CA_Total"].values, features["Nb_Clients"].values)

    if "Cpt Client" in base.columns:
        by_client = base.groupby([entity_col, "Cpt Client"])["Montant"].sum().reset_index()
        total = by_client.groupby(entity_col)["Montant"].sum()
        top = by_client.groupby(entity_col)["Montant"].max()
        features["Concentration_Client"] = features["Entity"].map(((top / total) * 100).fillna(0)).fillna(0)
    else:
        features["Concentration_Client"] = 0

    if "Nom Devise" in base.columns:
        total = base.groupby(entity_col)["Montant"].sum()
        non_eur = base[base["Nom Devise"].astype(str).str.upper() != "EUR"].groupby(entity_col)["Montant"].sum()
        features["Part_Non_EUR"] = features["Entity"].map(((non_eur / total) * 100).fillna(0)).fillna(0)
    else:
        features["Part_Non_EUR"] = 0

    if entity_col != "Famille" and "Famille" in base.columns:
        features["Segment_Detail"] = features["Entity"].map(base.groupby(entity_col)["Famille"].agg(lambda x: x.mode().iloc[0] if not x.mode().empty else "N/A")).fillna("N/A")
    else:
        features["Segment_Detail"] = ""

    feature_cols = [
        "CA_Total", "Qty_Total", "Nb_Commandes", "Nb_Clients", "Nb_Pays",
        "PU_Moyen", "PU_Pondere", "CA_Par_Client", "Lead_Time_Median",
        "Concentration_Client", "Part_Non_EUR",
    ]
    features = _clean_numeric(features, feature_cols)
    return features, feature_cols, "", entity_label


def _prepare_clustering_matrix(features: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    matrix = features[feature_cols].copy()
    for col in matrix.columns:
        matrix[col] = pd.to_numeric(matrix[col], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0)
        if col in {"CA_Total", "CA_Moyen", "Qty_Total", "Nb_Commandes", "Panier_Moyen", "PU_Pondere", "CA_Par_Client"}:
            matrix[col] = np.log1p(matrix[col].clip(lower=0))
    return matrix


def _choose_k(X_scaled: np.ndarray, max_k: int = 5) -> tuple[int, list[dict]]:
    n = X_scaled.shape[0]
    if n < 3:
        return 0, []
    upper = min(max_k, n - 1)
    metrics = []
    for k in range(2, upper + 1):
        labels = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=20).fit_predict(X_scaled)
        if len(set(labels)) < 2:
            continue
        metrics.append({"k": k, "silhouette": float(silhouette_score(X_scaled, labels))})
    if not metrics:
        return min(2, n), []
    best = max(metrics, key=lambda item: item["silhouette"])
    return int(best["k"]), metrics


def _business_label(entity_type: str, row: pd.Series, overall: pd.Series) -> tuple[str, str, str]:
    ca_high = row.get("CA_Total", 0) >= overall.get("CA_Total", 0)
    freq_high = row.get("Nb_Commandes", 0) >= overall.get("Nb_Commandes", 0)
    qty_high = row.get("Qty_Total", 0) >= overall.get("Qty_Total", 0)

    if entity_type == "clients":
        if ca_high and freq_high:
            return (
                "Clients stratégiques récurrents",
                "Ils combinent un CA élevé et une fréquence d'achat forte.",
                "À protéger avec un suivi commercial rapproché et des offres de fidélisation.",
            )
        if ca_high and not freq_high:
            return (
                "Gros tickets ponctuels",
                "Ils pèsent dans le CA mais commandent moins souvent.",
                "À travailler en récurrence avec des relances et contrats cadres.",
            )
        if not ca_high and freq_high:
            return (
                "Clients réguliers à développer",
                "Ils reviennent souvent mais avec des paniers plus modestes.",
                "À faire monter en panier via bundles, recommandations et upsell ciblé.",
            )
        return (
            "Clients occasionnels",
            "Leur contribution et leur fréquence restent limitées sur la période.",
            "À nourrir avec des campagnes simples et des offres de réactivation.",
        )

    if ca_high and qty_high:
        return (
            "Produits moteurs volume",
            "Ils génèrent beaucoup de CA avec des volumes solides.",
            "À sécuriser côté stock, disponibilité et visibilité commerciale.",
        )
    if ca_high and not qty_high:
        return (
            "Produits premium",
            "Ils tirent le CA avec une valeur unitaire élevée.",
            "À valoriser dans les offres et à surveiller côté marge.",
        )
    if not ca_high and qty_high:
        return (
            "Produits d'appel",
            "Ils tournent en volume mais contribuent moins au CA.",
            "À utiliser pour déclencher des ventes additionnelles.",
        )
    return (
        "Long tail produits",
        "Ils restent plus discrets sur la période.",
        "À arbitrer entre maintien catalogue, regroupement ou animation ciblée.",
    )


def _cluster_scatter(features: pd.DataFrame, X_scaled: np.ndarray, entity_label: str) -> str | None:
    try:
        import plotly.express as px
        from sklearn.decomposition import PCA

        if X_scaled.shape[0] < 3:
            return None
        coords = PCA(n_components=2, random_state=RANDOM_STATE).fit_transform(X_scaled)
        data = features.copy()
        data["Axe 1"] = coords[:, 0]
        data["Axe 2"] = coords[:, 1]
        data["Groupe"] = data["Cluster_Label"]
        data["CA"] = data["CA_Total"]
        fig = px.scatter(
            data,
            x="Axe 1",
            y="Axe 2",
            color="Groupe",
            size="CA",
            hover_name="Entity",
            hover_data={"CA_Total": ":,.0f", "Nb_Commandes": ":,.0f", "Axe 1": False, "Axe 2": False},
            title=f"Carte des groupes - {entity_label.lower()}",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_layout(height=520, legend_title_text="Groupes")
        return _to_html(fig)
    except Exception:
        return None


def _cluster_distribution_chart(profiles: list[dict], entity_label_plural: str) -> str | None:
    try:
        import plotly.graph_objects as go
        labels = [p["name"] for p in profiles]
        values = [p["count"] for p in profiles]
        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.45, textinfo="label+percent")])
        fig.update_layout(title=f"Répartition des {entity_label_plural.lower()}", height=360)
        return _to_html(fig)
    except Exception:
        return None


def _profile_clusters(features: pd.DataFrame, entity_type: str, entity_label_plural: str) -> list[dict]:
    profiles = []
    overall = features[["CA_Total", "Qty_Total", "Nb_Commandes"]].median(numeric_only=True)
    for cluster_id in sorted(features["Cluster"].unique()):
        subset = features[features["Cluster"] == cluster_id].copy()
        center = subset.median(numeric_only=True)
        name, reading, action = _business_label(entity_type, center, overall)
        top_members = (
            subset.sort_values("CA_Total", ascending=False)
            .head(8)[["Entity", "CA_Total", "Nb_Commandes"]]
            .to_dict("records")
        )
        profiles.append({
            "id": int(cluster_id),
            "name": name,
            "count": int(len(subset)),
            "share": round(len(subset) / len(features) * 100, 1),
            "ca_total": float(subset["CA_Total"].sum()),
            "ca_median": float(subset["CA_Total"].median()),
            "orders_median": float(subset["Nb_Commandes"].median()),
            "qty_median": float(subset["Qty_Total"].median()),
            "basket_median": float(subset.get("Panier_Moyen", subset.get("PU_Pondere", pd.Series([0]))).median()),
            "reading": reading,
            "action": action,
            "top_members": top_members,
            "entity_label_plural": entity_label_plural,
        })
    profiles.sort(key=lambda p: p["ca_total"], reverse=True)
    for idx, profile in enumerate(profiles, start=1):
        profile["display_id"] = idx
        profile["cluster_label"] = f"Groupe {idx}"
    return profiles


def _run_static_cluster(
    df: pd.DataFrame,
    entity_type: str,
    entity_label_plural: str,
    entity_label_singular: str,
) -> dict:
    if entity_type == "products":
        features, feature_cols, error, derived_label = _build_product_sales_features(df)
        entity_label_singular = derived_label
        entity_label_plural = "Produits" if derived_label == "Produit" else "Familles produits"
    else:
        features, feature_cols, error = _build_client_sales_features(df)

    if error:
        return {"error": error, "features": pd.DataFrame()}
    if len(features) < 3:
        return {"error": f"Pas assez de {entity_label_plural.lower()} sur la période sélectionnée.", "features": features}

    matrix = _prepare_clustering_matrix(features, feature_cols)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(matrix)
    k, metrics = _choose_k(X_scaled)
    if k < 2:
        return {"error": "Pas assez de données pour former plusieurs groupes.", "features": features}

    labels = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=30, max_iter=500).fit_predict(X_scaled)
    features = features.copy()
    features["Cluster"] = labels

    profiles = _profile_clusters(features, entity_type, entity_label_plural)
    label_map = {profile["id"]: profile["cluster_label"] for profile in profiles}
    name_map = {profile["id"]: profile["name"] for profile in profiles}
    features["Cluster_Label"] = features["Cluster"].map(lambda c: f"{label_map.get(c, 'Groupe')} - {name_map.get(c, '')}")

    graphs = {
        "scatter": _cluster_scatter(features, X_scaled, entity_label_plural),
        "distribution": _cluster_distribution_chart(profiles, entity_label_plural),
    }

    summary_table = (
        features.sort_values("CA_Total", ascending=False)
        .head(60)[["Entity", "Cluster_Label", "CA_Total", "Nb_Commandes", "Qty_Total"]]
        .rename(columns={"Entity": entity_label_singular, "Cluster_Label": "Groupe", "CA_Total": "CA", "Nb_Commandes": "Commandes", "Qty_Total": "Quantite"})
        .to_dict("records")
    )

    return {
        "features": features,
        "profiles": profiles,
        "graphs": graphs,
        "metrics": metrics,
        "k": k,
        "entity_label_singular": entity_label_singular,
        "entity_label_plural": entity_label_plural,
        "summary_table": summary_table,
    }


def _period_features(df: pd.DataFrame, granularity: str, entity_type: str) -> tuple[dict[str, pd.DataFrame], list[str], str, str]:
    col = _period_col(granularity)
    frames = {}
    entity_label_plural = "Clients" if entity_type == "clients" else "Produits"
    entity_label_singular = "Client" if entity_type == "clients" else "Produit"
    if col not in df.columns:
        return {}, [], entity_label_singular, entity_label_plural
    for period in _sorted_period_values(df[col].dropna().unique(), granularity):
        sub = df[df[col].astype(str) == str(period)].copy()
        if entity_type == "products":
            features, feature_cols, _, derived = _build_product_sales_features(sub)
            entity_label_singular = derived
            entity_label_plural = "Produits" if derived == "Produit" else "Familles produits"
        else:
            features, feature_cols, _ = _build_client_sales_features(sub)
        if len(features) >= 3:
            frames[period] = features
    return frames, feature_cols if frames else [], entity_label_singular, entity_label_plural


def _temporal_count_chart(distribution: list[dict]) -> str | None:
    try:
        import plotly.express as px
        df = pd.DataFrame(distribution)
        if df.empty:
            return None
        fig = px.bar(
            df,
            x="period",
            y="count",
            color="cluster_label",
            title="Évolution de la taille des groupes",
            labels={"period": "Période", "count": "Nombre", "cluster_label": "Groupe"},
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_layout(height=420, barmode="stack", legend_title_text="Groupes")
        return _to_html(fig)
    except Exception:
        return None


def _temporal_ca_chart(distribution: list[dict]) -> str | None:
    try:
        import plotly.express as px
        df = pd.DataFrame(distribution)
        if df.empty:
            return None
        fig = px.line(
            df,
            x="period",
            y="ca_total",
            color="cluster_label",
            markers=True,
            title="Évolution du CA par groupe",
            labels={"period": "Période", "ca_total": "CA", "cluster_label": "Groupe"},
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_layout(height=420, legend_title_text="Groupes")
        return _to_html(fig)
    except Exception:
        return None


def _transition_heatmap(transitions: list[dict]) -> str | None:
    try:
        import plotly.graph_objects as go
        if not transitions:
            return None
        first = transitions[0]
        matrix = first["matrix"]
        labels = list(matrix.index)
        fig = go.Figure(data=go.Heatmap(z=matrix.values, x=labels, y=labels, colorscale="Blues", text=matrix.values, texttemplate="%{text}"))
        fig.update_layout(title=f"Transitions {first['from']} → {first['to']}", xaxis_title="Groupe suivant", yaxis_title="Groupe précédent", height=420)
        return _to_html(fig)
    except Exception:
        return None


_TRACK_METRICS = [
    ("CA_Total", "CA"),
    ("Qty_Total", "Quantité"),
    ("Nb_Commandes", "Commandes"),
    ("Panier_Moyen", "Panier moyen"),
    ("PU_Pondere", "PU pondéré"),
    ("PU_Moyen", "PU moyen"),
    ("Nb_Familles", "Familles"),
    ("Nb_Clients", "Clients"),
    ("Lead_Time_Median", "Lead time"),
    ("Part_Non_EUR", "Part non-EUR"),
    ("Concentration_Client", "Concentration client"),
]


def _journey_chart(track_records: list[dict], k: int) -> str | None:
    try:
        import plotly.graph_objects as go
        if not track_records:
            return None
        df = pd.DataFrame(track_records)
        fig = go.Figure()
        for entity, data in df.groupby("entity", sort=False):
            fig.add_trace(
                go.Scatter(
                    x=data["period"],
                    y=data["cluster_num"],
                    mode="lines+markers",
                    name=str(entity),
                    text=data["cluster_label"],
                    customdata=data[["ca_total"]].values,
                    hovertemplate=(
                        "<b>%{fullData.name}</b><br>"
                        "Période: %{x}<br>"
                        "Groupe: %{text}<br>"
                        "CA: %{customdata[0]:,.0f} €<extra></extra>"
                    ),
                )
            )
        fig.update_layout(
            title="Parcours des éléments suivis entre les groupes",
            height=420,
            yaxis=dict(
                title="Groupe",
                tickmode="array",
                tickvals=list(range(1, k + 1)),
                ticktext=[f"Groupe {idx}" for idx in range(1, k + 1)],
            ),
            xaxis_title="Période",
            legend_title_text="Sélection",
        )
        return _to_html(fig)
    except Exception:
        return None


def _build_tracking_payload(
    assignments: dict[str, pd.DataFrame],
    periods: list[str],
    feature_cols: list[str],
    selected_entities: list[str] | None,
    k: int,
) -> dict:
    if not assignments:
        return {"options": [], "selected": [], "records": [], "changes": [], "chart": None}

    combined = []
    for period, frame in assignments.items():
        tmp = frame.copy()
        tmp["Period"] = period
        combined.append(tmp)
    all_rows = pd.concat(combined, ignore_index=True)

    top_entities = (
        all_rows.groupby("Entity")["CA_Total"]
        .sum()
        .sort_values(ascending=False)
    )
    options = [
        {"value": str(entity), "label": str(entity)}
        for entity in top_entities.head(300).index
    ]
    valid = set(str(entity) for entity in top_entities.index)
    selected = [str(entity) for entity in (selected_entities or []) if str(entity) in valid]
    if not selected:
        selected = [str(entity) for entity in top_entities.head(5).index]
    selected = selected[:12]

    metric_cols = [col for col, _label in _TRACK_METRICS if col in all_rows.columns]
    rows = all_rows[all_rows["Entity"].astype(str).isin(selected)].copy()
    rows["Entity"] = rows["Entity"].astype(str)
    rows["cluster_num"] = pd.to_numeric(rows["Cluster"], errors="coerce").fillna(0).astype(int) + 1

    records = [
        {
            "entity": row["Entity"],
            "period": row["Period"],
            "cluster": int(row["Cluster"]),
            "cluster_num": int(row["cluster_num"]),
            "cluster_label": row.get("Cluster_Label", f"Groupe {int(row['cluster_num'])}"),
            "ca_total": float(row.get("CA_Total", 0) or 0),
        }
        for _, row in rows.sort_values(["Entity", "Period"]).iterrows()
    ]

    changes = []
    for entity in selected:
        entity_rows = rows[rows["Entity"] == entity].copy()
        order_map = {period: idx for idx, period in enumerate(periods)}
        entity_rows["_order"] = entity_rows["Period"].map(order_map)
        entity_rows = entity_rows.sort_values("_order")
        previous = None
        for _, current in entity_rows.iterrows():
            if previous is not None and int(previous["Cluster"]) != int(current["Cluster"]):
                metric_changes = []
                for col, label in _TRACK_METRICS:
                    if col not in metric_cols:
                        continue
                    before = float(previous.get(col, 0) or 0)
                    after = float(current.get(col, 0) or 0)
                    delta = after - before
                    pct = (delta / abs(before) * 100) if abs(before) > 1e-9 else None
                    weight = abs(pct) if pct is not None else abs(delta)
                    metric_changes.append({
                        "metric": label,
                        "before": before,
                        "after": after,
                        "delta": delta,
                        "pct": pct,
                        "weight": weight,
                    })
                metric_changes = sorted(metric_changes, key=lambda item: item["weight"], reverse=True)[:4]
                changes.append({
                    "entity": entity,
                    "from_period": previous["Period"],
                    "to_period": current["Period"],
                    "from_cluster": f"Groupe {int(previous['Cluster']) + 1}",
                    "to_cluster": f"Groupe {int(current['Cluster']) + 1}",
                    "metrics": metric_changes,
                })
            previous = current

    return {
        "options": options,
        "selected": selected,
        "records": records,
        "changes": changes[:50],
        "chart": _journey_chart(records, k),
    }


def _run_temporal_cluster(
    df: pd.DataFrame,
    granularity: str,
    entity_type: str,
    selected_entities: list[str] | None = None,
) -> dict:
    frames, feature_cols, entity_label_singular, entity_label_plural = _period_features(df, granularity, entity_type)
    periods = list(frames.keys())
    if len(periods) < 2:
        return {"error": "Le clustering temporel nécessite au moins deux périodes avec assez de données."}

    min_count = min(len(frame) for frame in frames.values())
    if min_count < 3:
        return {"error": "Pas assez d'éléments récurrents pour suivre les groupes dans le temps."}

    all_features = pd.concat(frames.values(), ignore_index=True)
    matrix_all = _prepare_clustering_matrix(all_features, feature_cols)
    scaler = StandardScaler()
    scaler.fit(matrix_all)
    pooled_scaled = scaler.transform(matrix_all)
    k, _ = _choose_k(pooled_scaled, max_k=min(5, min_count - 1))
    k = max(2, min(k, min_count - 1))

    assignments = {}
    previous_centers = None
    distribution = []
    profiles_by_period = []

    for period in periods:
        features = frames[period].copy()
        X = scaler.transform(_prepare_clustering_matrix(features, feature_cols))
        km = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=30, max_iter=500)
        raw_labels = km.fit_predict(X)
        centers = km.cluster_centers_

        if previous_centers is not None:
            cost = np.linalg.norm(centers[:, None, :] - previous_centers[None, :, :], axis=2)
            row_ind, col_ind = linear_sum_assignment(cost)
            mapping = {int(row): int(col) for row, col in zip(row_ind, col_ind)}
            labels = np.array([mapping.get(int(label), int(label)) for label in raw_labels])
            aligned_centers = np.zeros_like(centers)
            for old, new in mapping.items():
                aligned_centers[new] = centers[old]
            previous_centers = aligned_centers
        else:
            labels = raw_labels
            previous_centers = centers

        features["Cluster"] = labels
        period_profiles = _profile_clusters(features, entity_type, entity_label_plural)
        for profile in period_profiles:
            profile["cluster_label"] = f"Groupe {int(profile['id']) + 1}"
        label_map = {profile["id"]: profile["cluster_label"] for profile in period_profiles}
        features["Cluster_Label"] = features["Cluster"].map(lambda c: label_map.get(c, f"Groupe {int(c) + 1}"))
        assignment_cols = ["Entity", "Cluster", "Cluster_Label", "CA_Total"] + [
            col for col, _label in _TRACK_METRICS if col in features.columns
        ]
        assignments[period] = features[list(dict.fromkeys(assignment_cols))].copy()

        for profile in period_profiles:
            distribution.append({
                "period": period,
                "cluster": profile["id"],
                "cluster_label": profile["cluster_label"],
                "name": profile["name"],
                "count": profile["count"],
                "ca_total": profile["ca_total"],
            })
        profiles_by_period.append({"period": period, "profiles": period_profiles})

    transitions = []
    for prev, nxt in zip(periods, periods[1:]):
        a = assignments[prev][["Entity", "Cluster"]].rename(columns={"Cluster": "from_cluster"})
        b = assignments[nxt][["Entity", "Cluster"]].rename(columns={"Cluster": "to_cluster"})
        merged = a.merge(b, on="Entity", how="inner")
        if merged.empty:
            continue
        labels = [f"Groupe {idx + 1}" for idx in range(k)]
        matrix = pd.crosstab(merged["from_cluster"], merged["to_cluster"]).reindex(index=range(k), columns=range(k), fill_value=0)
        matrix.index = labels
        matrix.columns = labels
        stable = int((merged["from_cluster"] == merged["to_cluster"]).sum())
        total = int(len(merged))
        transitions.append({
            "from": prev,
            "to": nxt,
            "matrix": matrix,
            "matrix_records": matrix.reset_index().rename(columns={"index": "Groupe précédent"}).to_dict("records"),
            "stable": stable,
            "migrants": total - stable,
            "stable_pct": round(stable / total * 100, 1) if total else 0,
            "total": total,
        })

    graphs = {
        "temporal_counts": _temporal_count_chart(distribution),
        "temporal_ca": _temporal_ca_chart(distribution),
        "transition_heatmap": _transition_heatmap(transitions),
    }
    tracking = _build_tracking_payload(assignments, periods, feature_cols, selected_entities, k)
    graphs["journey"] = tracking.get("chart")

    latest_profiles = profiles_by_period[-1]["profiles"] if profiles_by_period else []
    return {
        "k": k,
        "periods": periods,
        "profiles": latest_profiles,
        "profiles_by_period": profiles_by_period,
        "distribution": distribution,
        "transitions": transitions,
        "tracking": tracking,
        "graphs": graphs,
        "entity_label_singular": entity_label_singular,
        "entity_label_plural": entity_label_plural,
    }


def generate_sales_clustering_analysis(
    df: pd.DataFrame,
    mode: str = "static",
    entity_type: str = "clients",
    granularity: str = "month",
    period: str | None = None,
    period_start: str | None = None,
    period_end: str | None = None,
    tracked_entities: list[str] | None = None,
) -> dict:
    """Business-first clustering for the Sales Analytics UI."""
    try:
        if df is None or df.empty:
            return {"results": {}, "graphs": {}, "kpis": {}, "error": "Aucune donnée disponible."}

        mode = "temporal" if mode == "temporal" else "static"
        entity_type = "products" if entity_type == "products" else "clients"
        granularity = granularity if granularity in _PERIOD_COLUMNS else "month"
        period_options = get_sales_clustering_period_options(df)

        available = period_options.get(granularity, [])
        if mode == "static":
            if period in available and not period_start and not period_end:
                start = end = period
            else:
                start = period_start if period_start in available else (available[-1] if available else None)
                end = period_end if period_end in available else start
            start, end = _order_period_bounds(available, start, end)
            scoped = _filter_period_range(df, granularity, start, end)
            entity_label_plural = "Clients" if entity_type == "clients" else "Produits"
            entity_label_singular = "Client" if entity_type == "clients" else "Produit"
            result = _run_static_cluster(scoped, entity_type, entity_label_plural, entity_label_singular)
            if result.get("error"):
                return {"results": {}, "graphs": {}, "kpis": {}, "error": result["error"], "period_options": period_options}

            kpis = {
                "mode_label": "Clustering Statique",
                "entity_label": result["entity_label_plural"],
                "entity_count": int(len(result["features"])),
                "clusters": int(result["k"]),
                "period_label": start if start == end else f"{start} → {end}",
                "granularity_label": _GRANULARITY_LABELS.get(granularity, "Période"),
                "ca_total": _money(result["features"]["CA_Total"].sum()),
            }
            results = {
                "profiles": result["profiles"],
                "summary_table": result["summary_table"],
                "metrics": result.get("metrics", []),
                "entity_label_singular": result["entity_label_singular"],
                "entity_label_plural": result["entity_label_plural"],
            }
            return {
                "results": results,
                "graphs": result["graphs"],
                "kpis": kpis,
                "error": None,
                "period_options": period_options,
                "resolved": {"period": start, "period_start": start, "period_end": end},
            }

        start = period_start if period_start in available else (available[0] if available else None)
        end = period_end if period_end in available else (available[-1] if available else None)
        start, end = _order_period_bounds(available, start, end)
        scoped = _filter_period_range(df, granularity, start, end)
        result = _run_temporal_cluster(scoped, granularity, entity_type, selected_entities=tracked_entities)
        if result.get("error"):
            return {"results": {}, "graphs": {}, "kpis": {}, "error": result["error"], "period_options": period_options}

        kpis = {
            "mode_label": "Clustering temporel",
            "entity_label": result["entity_label_plural"],
            "entity_count": int(max([sum(item["count"] for item in period["profiles"]) for period in result["profiles_by_period"]] or [0])),
            "clusters": int(result["k"]),
            "period_label": f"{start} → {end}",
            "granularity_label": _GRANULARITY_LABELS.get(granularity, "Période"),
            "period_count": len(result["periods"]),
        }
        results = {
            "profiles": result["profiles"],
            "profiles_by_period": result["profiles_by_period"],
            "distribution": result["distribution"],
            "transitions": result["transitions"],
            "tracking": result["tracking"],
            "periods": result["periods"],
            "entity_label_singular": result["entity_label_singular"],
            "entity_label_plural": result["entity_label_plural"],
        }
        return {
            "results": results,
            "graphs": result["graphs"],
            "kpis": kpis,
            "error": None,
            "period_options": period_options,
            "resolved": {"period_start": start, "period_end": end},
            "tracked_entities": result.get("tracking", {}).get("selected", []),
        }

    except Exception as e:
        return {"results": {}, "graphs": {}, "kpis": {}, "error": str(e)}
