import base64
from io import BytesIO

import numpy as np
import pandas as pd


def _fig_to_base64_png(fig) -> str:
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=160, bbox_inches='tight')
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')


def plot_client_timeline(series: list[dict], client_id: str, granularity: str) -> str | None:
    """Graph 2x2 des métriques (valeurs) + points rouges sur périodes anormales."""
    if not series:
        return None

    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except Exception:
        return None

    df = pd.DataFrame(series).copy()
    if df.empty or 'period' not in df.columns:
        return None

    df['period'] = df['period'].astype(str)

    metrics = [
        ('ca', 'is_anomaly_ca', 'CA'),
        ('freq', 'is_anomaly_freq', 'Fréquence'),
        ('qty', 'is_anomaly_qty', 'Quantité'),
        ('price', 'is_anomaly_price', 'Prix'),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(12, 6), sharex=True)
    axes = axes.ravel()

    x = np.arange(len(df))
    xlabels = df['period'].tolist()

    for ax, (val_col, flag_col, title) in zip(axes, metrics, strict=False):
        if val_col not in df.columns:
            ax.axis('off')
            continue

        y = pd.to_numeric(df[val_col], errors='coerce')
        ax.plot(x, y, linewidth=1.5)

        if flag_col in df.columns:
            mask = df[flag_col].fillna(False).astype(bool) & y.notna()
            if mask.any():
                ax.scatter(x[mask.to_numpy()], y[mask], color='red', s=20, zorder=3)

        ax.set_title(title)
        ax.grid(True, alpha=0.2)

    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels(xlabels, rotation=45, ha='right')

    fig.suptitle(f"Timeline anomalies — client {client_id} ({granularity})", y=1.02)
    fig.tight_layout()

    png = _fig_to_base64_png(fig)
    plt.close(fig)
    return png


def plot_multi_clients_anomaly_counts(reports: list[dict], granularity: str) -> str | None:
    """Barres empilées: nb d'anomalies par métrique et par client."""
    if not reports:
        return None

    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except Exception:
        return None

    rows = []
    for rep in reports:
        client_id = ((rep.get('client') or {}).get('id')) or '—'
        kpis = rep.get('kpis') or {}
        rows.append(
            {
                'client': str(client_id),
                'CA': int(kpis.get('n_anomalies_ca') or 0),
                'Freq': int(kpis.get('n_anomalies_freq') or 0),
                'Qty': int(kpis.get('n_anomalies_qty') or 0),
                'Price': int(kpis.get('n_anomalies_price') or 0),
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return None

    df = df.sort_values(['CA', 'Freq', 'Qty', 'Price'], ascending=False)

    fig, ax = plt.subplots(figsize=(12, 5))
    x = np.arange(len(df))

    bottom = np.zeros(len(df))
    for col, label in [('CA', 'CA'), ('Freq', 'Fréq.'), ('Qty', 'Qté'), ('Price', 'Prix')]:
        vals = df[col].to_numpy(dtype=float)
        ax.bar(x, vals, bottom=bottom, label=label)
        bottom += vals

    ax.set_xticks(x)
    ax.set_xticklabels(df['client'].tolist(), rotation=45, ha='right')
    ax.set_ylabel("Nombre d'anomalies")
    ax.set_title(f"Anomalies détectées — clients sélectionnés ({granularity})")
    ax.grid(True, axis='y', alpha=0.2)
    ax.legend(ncol=4, fontsize=9)

    fig.tight_layout()
    png = _fig_to_base64_png(fig)
    plt.close(fig)
    return png


def plot_top_anomalies(rows: list[dict], granularity: str, title: str) -> str | None:
    """Barres horizontales: score des top anomalies (global)."""
    if not rows:
        return None

    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except Exception:
        return None

    labels = []
    scores = []
    for r in rows:
        client = r.get('client')
        period = r.get('period')
        score = r.get('score')
        if score is None or (isinstance(score, float) and np.isnan(score)):
            continue
        labels.append(f"{client} — {period}")
        scores.append(float(score))

    if not scores:
        return None

    # Limiter le nombre de barres
    labels = labels[:20]
    scores = scores[:20]

    fig, ax = plt.subplots(figsize=(12, 6))
    y = np.arange(len(scores))
    ax.barh(y, scores)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel('Score (z robuste)')
    ax.set_title(f"{title} ({granularity})")
    ax.grid(True, axis='x', alpha=0.2)

    fig.tight_layout()
    png = _fig_to_base64_png(fig)
    plt.close(fig)
    return png
