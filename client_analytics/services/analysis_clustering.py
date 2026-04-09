"""
Service pour l'onglet CLUSTERING
Clustering K-Means automatique avec feature engineering avancé
Adapté du notebook week_1_clean.ipynb
"""
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (
    silhouette_score,
    davies_bouldin_score,
    calinski_harabasz_score,
)

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
        # 1) Feature engineering
        df_client, top_familles = build_client_features(df)
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


def generate_clustering_tab_analysis(df):
    """Alias pour compatibilité."""
    return generate_clustering_analysis(df)
