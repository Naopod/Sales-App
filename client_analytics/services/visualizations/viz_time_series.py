"""
Visualisations pour le sous-onglet SÉRIE TEMPORELLE
"""
from __future__ import annotations

import logging

import base64
import io

import matplotlib

# Backend non-interactif (serveur Django)
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

try:
    from statsmodels.tsa.seasonal import STL
except Exception:
    STL = None


def _encode_fig_to_img_html(fig, alt: str) -> str:
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png', facecolor=fig.get_facecolor(), bbox_inches='tight')
    plt.close(fig)
    buffer.seek(0)
    img_b64 = base64.b64encode(buffer.read()).decode('ascii')
    return (
        f'<img src="data:image/png;base64,{img_b64}" '
        f'alt="{alt}" style="width:100%;height:auto;" />'
    )


def _compute_strength(component: pd.Series, resid: pd.Series) -> float | None:
    """Force Cleveland (trend/seasonal).

    var_resid = Var(resid)
    strength = max(0, 1 - var_resid / Var(component + resid))
    """
    try:
        resid_v = pd.to_numeric(resid, errors='coerce').dropna().values
        comp_v = pd.to_numeric(component, errors='coerce').dropna().values
        if len(resid_v) < 10 or len(comp_v) < 10:
            return None
        # aligner sur min longueur si nécessaire
        n = min(len(resid_v), len(comp_v))
        resid_v = resid_v[-n:]
        comp_v = comp_v[-n:]
        var_resid = float(pd.Series(resid_v).var(ddof=0))
        var_denom = float(pd.Series(comp_v + resid_v).var(ddof=0))
        if var_denom <= 0:
            return None
        strength = max(0.0, 1.0 - (var_resid / var_denom))
        return round(strength, 3)
    except Exception:
        return None


def create_stl_decomposition_plot(df_daily: pd.DataFrame, df_display: pd.DataFrame, display_granularity: str = 'month'):
    """
    Crée un HTML combiné:
    - évolution du CA agrégé (df_display) pour le sous-onglet
    - décomposition STL calculée sur la série JOURNALIÈRE (df_daily)

    Note: on génère volontairement une image (PNG base64) plutôt qu'un
    graphique Plotly afin d'éviter les problèmes de rendu côté navigateur
    (Plotly/CDN/CSP/JS désactivé, onglets Bootstrap masqués, etc.).
    
    Args:
        df_daily: DataFrame journalier (DatetimeIndex) avec CA_Total
        df_display: DataFrame agrégé pour l'affichage (index str ou period)
        display_granularity: 'month' | 'quarter' | 'year'

    Returns:
        tuple[str|None, dict]: (html, metrics_dict)
    """
    metrics = {}
    if (
        df_daily is None
        or df_display is None
        or 'CA_Total' not in getattr(df_daily, 'columns', [])
        or 'CA_Total' not in getattr(df_display, 'columns', [])
        or len(df_daily) < 2
        or len(df_display) < 2
    ):
        return None, metrics
        
    try:
        # ---- STL sur daily (fallback si indisponible / trop court / constant) ----
        df_d = df_daily.copy()
        if not isinstance(df_d.index, pd.DatetimeIndex):
            df_d.index = pd.to_datetime(df_d.index, errors='coerce')
        df_d = df_d.sort_index()

        y_daily = pd.to_numeric(df_d['CA_Total'], errors='coerce').fillna(0)

        can_stl = STL is not None and len(y_daily) >= 14 and y_daily.nunique(dropna=True) > 1

        if can_stl:
            stl_period = 7
            if len(y_daily) >= 2 * 365:
                stl_period = 365

            stl = STL(y_daily, period=stl_period, robust=True)
            stl_res = stl.fit()

            metrics['stl_period'] = int(stl_period)
            metrics['stl_trend_strength'] = _compute_strength(stl_res.trend, stl_res.resid)
            metrics['stl_seasonal_strength'] = _compute_strength(stl_res.seasonal, stl_res.resid)

            fig2, axes = plt.subplots(4, 1, figsize=(10, 7), dpi=150, sharex=True)
            fig2.patch.set_facecolor('#141E32')
            for ax in axes:
                ax.set_facecolor('#1E283C')
                ax.grid(True, which='major', axis='both', alpha=0.12, color='white')
                for spine in ax.spines.values():
                    spine.set_color((1, 1, 1, 0.2))

            axes[0].plot(stl_res.observed.index, stl_res.observed.values, color='#2E86AB', linewidth=1.2)
            axes[0].set_title('Observed (daily)', color='white', fontsize=11, fontweight='bold')

            axes[1].plot(stl_res.trend.index, stl_res.trend.values, color='#F18F01', linewidth=1.2)
            axes[1].set_title('Trend (daily)', color='white', fontsize=11, fontweight='bold')

            axes[2].plot(stl_res.seasonal.index, stl_res.seasonal.values, color='#9B5DE5', linewidth=1.0)
            axes[2].set_title('Seasonal (daily)', color='white', fontsize=11, fontweight='bold')

            axes[3].plot(stl_res.resid.index, stl_res.resid.values, color='#00BBF9', linewidth=0.9)
            axes[3].set_title('Resid (daily)', color='white', fontsize=11, fontweight='bold')

            for ax in axes:
                ax.tick_params(axis='x', colors='white')
                ax.tick_params(axis='y', colors='white')

            # Axe X lisible (mois/année) sur TOUS les subplots.
            # Sinon les labels n'apparaissent que sur le dernier (Resid) et semblent "absents"
            # si l'utilisateur ne scroll pas jusqu'en bas.
            try:
                locator = mdates.AutoDateLocator(minticks=3, maxticks=8)
                formatter = mdates.ConciseDateFormatter(locator)
                for ax in axes:
                    ax.xaxis.set_major_locator(locator)
                    ax.xaxis.set_major_formatter(formatter)
                    ax.tick_params(axis='x', labelbottom=True)
                    for lbl in ax.get_xticklabels():
                        lbl.set_rotation(45)
                        lbl.set_ha('right')
                        lbl.set_color('white')
            except Exception:
                pass
            fig2.tight_layout()
        else:
            # fallback: CA daily + moyenne mobile
            rolling_w = 7 if len(y_daily) >= 7 else 2
            y_ma_d = y_daily.rolling(window=rolling_w, min_periods=1).mean()

            fig2, ax2 = plt.subplots(figsize=(10, 4), dpi=150)
            fig2.patch.set_facecolor('#141E32')
            ax2.set_facecolor('#1E283C')
            ax2.plot(df_d.index, y_daily, linewidth=1.3, color='#2E86AB', label='CA daily')
            ax2.plot(df_d.index, y_ma_d, linestyle='--', linewidth=1.1, color='#F18F01', label='MA')
            ax2.set_title("CA journalier (fallback)", color='white', fontsize=12, fontweight='bold')
            ax2.tick_params(axis='x', colors='white')
            ax2.tick_params(axis='y', colors='white')
            try:
                locator = mdates.AutoDateLocator(minticks=3, maxticks=8)
                formatter = mdates.ConciseDateFormatter(locator)
                ax2.xaxis.set_major_locator(locator)
                ax2.xaxis.set_major_formatter(formatter)
                for lbl in ax2.get_xticklabels():
                    lbl.set_rotation(45)
                    lbl.set_ha('right')
            except Exception:
                pass
            ax2.grid(True, which='major', axis='both', alpha=0.15, color='white')
            for spine in ax2.spines.values():
                spine.set_color((1, 1, 1, 0.2))
            legend2 = ax2.legend(loc='upper left', frameon=False)
            for text in legend2.get_texts():
                text.set_color('white')
            fig2.tight_layout()

        html2 = _encode_fig_to_img_html(fig2, "STL / fallback")

        html = (
            '<div class="timeseries-chart">'
            '<div class="small text-muted mb-1">Décomposition STL (sur daily) / fallback</div>'
            f'{html2}'
            '</div>'
        )
        return html, metrics
        
    except Exception as e:
        logger.exception("Erreur lors de la création du graphique STL/fallback")
        return None, {}


def create_metric_stl_decomposition_plot(
    df_daily: pd.DataFrame,
    df_display: pd.DataFrame,
    value_col: str,
    display_granularity: str = 'month',
    metric_name: str | None = None,
    y_label: str | None = None,
):
    """Version paramétrable de `create_stl_decomposition_plot`.

    Génère une image de la courbe agrégée (df_display[value_col]) + une image
    STL (ou fallback) sur la série journalière (df_daily[value_col]).
    """
    metrics = {}
    if metric_name is None:
        metric_name = value_col
    if y_label is None:
        y_label = metric_name

    if (
        df_daily is None
        or df_display is None
        or value_col not in getattr(df_daily, 'columns', [])
        or value_col not in getattr(df_display, 'columns', [])
        or len(df_daily) < 2
        or len(df_display) < 2
    ):
        return None, metrics

    try:
        # ---- 1) Courbe agrégée (affichage) ----
        df_disp = df_display.copy().sort_index()
        x_labels = df_disp.index.astype(str).tolist()
        y_values = pd.to_numeric(df_disp[value_col], errors='coerce').fillna(0)

        rolling_window = 3 if len(df_disp) >= 3 else 2
        y_ma = y_values.rolling(window=rolling_window, min_periods=1).mean()

        fig1, ax1 = plt.subplots(figsize=(10, 4), dpi=150)
        fig1.patch.set_facecolor('#141E32')
        ax1.set_facecolor('#1E283C')

        ax1.plot(x_labels, y_values, marker='o', linewidth=2.5, color='#2E86AB', label=f"{metric_name} agrégé")
        ax1.plot(x_labels, y_ma, linestyle='--', linewidth=2, color='#F18F01', label='Moyenne mobile')

        title_map = {'month': 'mensuel', 'quarter': 'trimestriel', 'year': 'année fiscale'}
        title_suffix = title_map.get(display_granularity, display_granularity)
        ax1.set_title(f"Évolution {metric_name} ({title_suffix})", color='white', fontsize=12, fontweight='bold')
        ax1.set_xlabel('Période', color='white')
        ax1.set_ylabel(y_label, color='white')
        ax1.tick_params(axis='x', labelrotation=45, colors='white')
        ax1.tick_params(axis='y', colors='white')
        ax1.grid(True, which='major', axis='both', alpha=0.15, color='white')
        for spine in ax1.spines.values():
            spine.set_color((1, 1, 1, 0.2))

        legend1 = ax1.legend(loc='upper left', frameon=False)
        for text in legend1.get_texts():
            text.set_color('white')
        fig1.tight_layout()

        # ---- 2) STL sur daily (fallback si indisponible / trop court / constant) ----
        df_d = df_daily.copy()
        if not isinstance(df_d.index, pd.DatetimeIndex):
            df_d.index = pd.to_datetime(df_d.index, errors='coerce')
        df_d = df_d.sort_index()

        y_daily = pd.to_numeric(df_d[value_col], errors='coerce').fillna(0)
        can_stl = STL is not None and len(y_daily) >= 14 and y_daily.nunique(dropna=True) > 1

        if can_stl:
            stl_period = 7
            if len(y_daily) >= 2 * 365:
                stl_period = 365

            stl = STL(y_daily, period=stl_period, robust=True)
            stl_res = stl.fit()

            metrics['stl_period'] = int(stl_period)
            metrics['stl_trend_strength'] = _compute_strength(stl_res.trend, stl_res.resid)
            metrics['stl_seasonal_strength'] = _compute_strength(stl_res.seasonal, stl_res.resid)

            fig2, axes = plt.subplots(4, 1, figsize=(10, 7), dpi=150, sharex=True)
            fig2.patch.set_facecolor('#141E32')
            for ax in axes:
                ax.set_facecolor('#1E283C')
                ax.grid(True, which='major', axis='both', alpha=0.12, color='white')
                for spine in ax.spines.values():
                    spine.set_color((1, 1, 1, 0.2))

            axes[0].plot(stl_res.observed.index, stl_res.observed.values, color='#2E86AB', linewidth=1.2)
            axes[0].set_title(f'Observed (daily) - {metric_name}', color='white', fontsize=11, fontweight='bold')

            axes[1].plot(stl_res.trend.index, stl_res.trend.values, color='#F18F01', linewidth=1.2)
            axes[1].set_title('Trend (daily)', color='white', fontsize=11, fontweight='bold')

            axes[2].plot(stl_res.seasonal.index, stl_res.seasonal.values, color='#9B5DE5', linewidth=1.0)
            axes[2].set_title('Seasonal (daily)', color='white', fontsize=11, fontweight='bold')

            axes[3].plot(stl_res.resid.index, stl_res.resid.values, color='#00BBF9', linewidth=0.9)
            axes[3].set_title('Resid (daily)', color='white', fontsize=11, fontweight='bold')

            for ax in axes:
                ax.tick_params(axis='x', colors='white')
                ax.tick_params(axis='y', colors='white')

            # Axe X lisible
            try:
                locator = mdates.AutoDateLocator(minticks=3, maxticks=8)
                formatter = mdates.ConciseDateFormatter(locator)
                for ax in axes:
                    ax.xaxis.set_major_locator(locator)
                    ax.xaxis.set_major_formatter(formatter)
                    ax.tick_params(axis='x', labelbottom=True)
                    for lbl in ax.get_xticklabels():
                        lbl.set_rotation(45)
                        lbl.set_ha('right')
                        lbl.set_color('white')
            except Exception:
                pass
            fig2.tight_layout()
        else:
            rolling_w = 7 if len(y_daily) >= 7 else 2
            y_ma_d = y_daily.rolling(window=rolling_w, min_periods=1).mean()

            fig2, ax2 = plt.subplots(figsize=(10, 4), dpi=150)
            fig2.patch.set_facecolor('#141E32')
            ax2.set_facecolor('#1E283C')
            ax2.plot(df_d.index, y_daily, linewidth=1.3, color='#2E86AB', label=f'{metric_name} daily')
            ax2.plot(df_d.index, y_ma_d, linestyle='--', linewidth=1.1, color='#F18F01', label='MA')
            ax2.set_title(f"{metric_name} journalier (fallback)", color='white', fontsize=12, fontweight='bold')
            ax2.tick_params(axis='x', colors='white')
            ax2.tick_params(axis='y', colors='white')
            try:
                locator = mdates.AutoDateLocator(minticks=3, maxticks=8)
                formatter = mdates.ConciseDateFormatter(locator)
                ax2.xaxis.set_major_locator(locator)
                ax2.xaxis.set_major_formatter(formatter)
                for lbl in ax2.get_xticklabels():
                    lbl.set_rotation(45)
                    lbl.set_ha('right')
                    lbl.set_color('white')
            except Exception:
                pass
            ax2.grid(True, which='major', axis='both', alpha=0.15, color='white')
            for spine in ax2.spines.values():
                spine.set_color((1, 1, 1, 0.2))
            legend2 = ax2.legend(loc='upper left', frameon=False)
            for text in legend2.get_texts():
                text.set_color('white')
            fig2.tight_layout()

        html1 = _encode_fig_to_img_html(fig1, f"{metric_name} agrégé")
        html2 = _encode_fig_to_img_html(fig2, f"STL / fallback - {metric_name}")
        html = (
            '<div class="timeseries-chart">'
            '<div class="small text-muted mb-1">Évolution (agrégé)</div>'
            f'{html1}'
            '<div class="small text-muted mt-3 mb-1">Décomposition STL (sur daily) / fallback</div>'
            f'{html2}'
            '</div>'
        )
        return html, metrics
    except Exception as e:
        logger.exception("Erreur lors de la création du graphique STL/fallback (%s)", metric_name)
        return None, {}


def create_anomaly_dashboard_plot(
    anom_map: dict[str, pd.DataFrame],
    title: str = "Détection d’anomalies (daily) — STL+MAD",
) -> str | None:
    """Crée un dashboard d’anomalies (PNG base64) pour plusieurs métriques."""
    if not anom_map:
        return None

    preferred = ["CA_Total", "Qty_Total", "Nb_Clients"]
    metrics = [m for m in preferred if m in anom_map] + [m for m in anom_map.keys() if m not in preferred]
    metrics = metrics[:3]
    if not metrics:
        return None

    name_map = {
        "CA_Total": "CA",
        "Qty_Total": "Quantité",
        "Nb_Clients": "Nb clients",
    }

    fig, axes = plt.subplots(len(metrics), 1, figsize=(10, 3.2 * len(metrics)), dpi=150, sharex=True)
    if len(metrics) == 1:
        axes = [axes]

    fig.patch.set_facecolor('#141E32')
    for ax in axes:
        ax.set_facecolor('#1E283C')
        ax.grid(True, which='major', axis='both', alpha=0.12, color='white')
        for spine in ax.spines.values():
            spine.set_color((1, 1, 1, 0.2))

    locator = mdates.AutoDateLocator(minticks=3, maxticks=8)
    formatter = mdates.ConciseDateFormatter(locator)

    for i, metric in enumerate(metrics):
        dfm = anom_map.get(metric)
        if dfm is None or dfm.empty:
            continue

        dfm_local = dfm.copy()
        if not isinstance(dfm_local.index, pd.DatetimeIndex):
            dfm_local.index = pd.to_datetime(dfm_local.index, errors='coerce')
        dfm_local = dfm_local.sort_index()

        x = dfm_local.index
        observed = pd.to_numeric(dfm_local.get("observed"), errors="coerce")
        expected = pd.to_numeric(dfm_local.get("expected"), errors="coerce")
        is_anom = dfm_local.get("is_anomaly")
        if is_anom is None:
            is_anom = pd.Series(False, index=dfm_local.index)
        is_anom = is_anom.fillna(False).astype(bool)

        direction = dfm_local.get("direction")
        if direction is None:
            direction = pd.Series("", index=dfm_local.index)

        ax = axes[i]
        ax.plot(x, observed, color='#2E86AB', linewidth=1.2, label='Observed')
        ax.plot(x, expected, color='#F18F01', linewidth=1.1, linestyle='--', label='Expected')

        if bool(is_anom.any()):
            spikes = is_anom & (direction.astype(str) == 'spike')
            drops = is_anom & (direction.astype(str) == 'drop')

            if bool(spikes.any()):
                ax.scatter(x[spikes], observed.loc[spikes], s=18, color='#9B5DE5', alpha=0.95, label='Anomaly (spike)', zorder=5)
            if bool(drops.any()):
                ax.scatter(x[drops], observed.loc[drops], s=18, color='#00BBF9', alpha=0.95, label='Anomaly (drop)', zorder=5)

        display_name = name_map.get(metric, metric)
        ax.set_title(display_name, color='white', fontsize=11, fontweight='bold')
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)
        ax.tick_params(axis='x', labelbottom=True)
        for lbl in ax.get_xticklabels():
            lbl.set_rotation(45)
            lbl.set_ha('right')
            lbl.set_color('white')

        leg = ax.legend(loc='upper left', frameon=False, fontsize=9)
        for text in leg.get_texts():
            text.set_color('white')

    fig.suptitle(title, color='white', fontsize=12, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    return _encode_fig_to_img_html(fig, alt=title)
