"""Détection d’anomalies robustes pour séries temporelles.

Méthode: STL (robust=True) + score robuste via MAD.

- Entrée principale: série journalière (DatetimeIndex) idéalement continue.
- Sortie: DataFrame par métrique avec observed/expected/resid/z/is_anomaly/direction.

Cette implémentation est conçue pour être:
- robuste aux outliers
- sans dépendances lourdes supplémentaires
- tolérante aux cas limites (série courte, constante, NaN, MAD=0)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

try:
    from statsmodels.tsa.seasonal import STL
except Exception:  # pragma: no cover
    STL = None


@dataclass(frozen=True)
class AnomalyParams:
    method: str = "stl+mad"
    z_thresh: float = 3.5
    basis: str = "daily"
    stl_period: int = 7
    min_points: int = 30


def _resolve_stl_period(n_points: int, stl_period: int | None) -> int:
    if stl_period is not None:
        return int(stl_period)
    # Règle métier demandée
    return 365 if n_points >= 2 * 365 else 7


def _safe_datetime_index(index: pd.Index) -> pd.DatetimeIndex:
    if isinstance(index, pd.DatetimeIndex):
        return index
    dt = pd.to_datetime(index, errors="coerce")
    return pd.DatetimeIndex(dt)


def detect_anomalies_stl_mad(
    series: pd.Series,
    stl_period: int | None = None,
    z_thresh: float = 3.5,
    min_points: int = 30,
) -> pd.DataFrame:
    """Détecte les anomalies d’une série via STL + MAD.

    Args:
        series: Série temporelle (index datetime recommandé).
        stl_period: Période STL. Si None, applique la règle 7/365 selon longueur.
        z_thresh: Seuil |z| au-delà duquel on marque une anomalie.
        min_points: Nombre minimal de points valides requis.

    Returns:
        DataFrame index datetime avec colonnes:
            observed, expected, resid, z, is_anomaly, direction
    """
    if series is None:
        series = pd.Series(dtype=float)

    s = pd.to_numeric(series, errors="coerce")
    if s.index is None:
        s.index = pd.RangeIndex(len(s))

    dt_index = _safe_datetime_index(s.index)
    s = pd.Series(s.values, index=dt_index, name="observed").sort_index()

    n_total = int(len(s))
    stl_period_resolved = _resolve_stl_period(n_total, stl_period)

    out = pd.DataFrame(index=s.index)
    out["observed"] = s.astype(float)

    valid = out["observed"].replace([np.inf, -np.inf], np.nan).dropna()
    if len(valid) < min_points or valid.nunique(dropna=True) <= 1:
        out["expected"] = np.nan
        out["resid"] = np.nan
        out["z"] = np.nan
        out["is_anomaly"] = False
        out["direction"] = ""
        return out

    # STL nécessite une série sans NaN -> on interpole légèrement si besoin
    y = out["observed"].copy()
    if y.isna().any():
        y = y.interpolate(limit_direction="both")

    expected: pd.Series
    resid: pd.Series

    can_stl = (
        STL is not None
        and len(y) >= max(14, 2 * stl_period_resolved)
        and y.nunique(dropna=True) > 1
    )

    if can_stl:
        try:
            stl = STL(y, period=stl_period_resolved, robust=True)
            stl_res = stl.fit()
            expected = (stl_res.trend + stl_res.seasonal).rename("expected")
            resid = (y - expected).rename("resid")
        except Exception:
            can_stl = False

    if not can_stl:
        window = 7 if len(y) >= 7 else max(2, int(min(len(y), 7)))
        expected = y.rolling(window=window, min_periods=1).mean().rename("expected")
        resid = (y - expected).rename("resid")

    out["expected"] = expected
    out["resid"] = resid

    resid_valid = pd.to_numeric(out["resid"], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    med = float(resid_valid.median())
    mad = float((resid_valid.sub(med).abs()).median())

    if mad <= 0 or not np.isfinite(mad):
        out["z"] = np.nan
        out["is_anomaly"] = False
        out["direction"] = ""
        return out

    z = 0.6745 * (out["resid"] - med) / mad
    out["z"] = z

    is_anom = z.abs() > float(z_thresh)
    is_anom = is_anom.fillna(False)
    out["is_anomaly"] = is_anom.astype(bool)

    direction = pd.Series("", index=out.index, dtype=str)
    direction.loc[is_anom & (out["resid"] > 0)] = "spike"
    direction.loc[is_anom & (out["resid"] < 0)] = "drop"
    out["direction"] = direction

    return out


def build_anomaly_report(
    df_daily: pd.DataFrame,
    value_cols: list[str] | None = None,
    z_thresh: float = 3.5,
) -> dict[str, Any]:
    """Construit un rapport multi-métriques + score joint (>=2 métriques anormales).

    Note: Le rapport retourné est destiné à être injecté dans `results['anomalies']`.

    Args:
        df_daily: DataFrame journalier (DatetimeIndex) avec colonnes métriques.
        value_cols: Colonnes à analyser.
        z_thresh: Seuil |z|.

    Returns:
        dict conforme à la structure demandée (params/by_metric/joint),
        + un champ interne `_anom_map` (DataFrames) pour la génération du dashboard.
    """
    if value_cols is None:
        value_cols = ["CA_Total", "Qty_Total", "Nb_Clients"]

    if df_daily is None or df_daily.empty:
        params = AnomalyParams(z_thresh=float(z_thresh), stl_period=7)
        return {
            "params": {
                "method": params.method,
                "z_thresh": params.z_thresh,
                "stl_period": params.stl_period,
                "basis": params.basis,
            },
            "by_metric": {},
            "joint": {"n_joint_ge_2": 0, "top_joint": []},
            "_anom_map": {},
        }

    df = df_daily.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, errors="coerce")
    df = df.sort_index()

    stl_period_resolved = _resolve_stl_period(len(df), None)
    params = AnomalyParams(z_thresh=float(z_thresh), stl_period=int(stl_period_resolved))

    by_metric: dict[str, Any] = {}
    anom_map: dict[str, pd.DataFrame] = {}

    for col in value_cols:
        if col not in df.columns:
            continue

        anom_df = detect_anomalies_stl_mad(
            df[col],
            stl_period=params.stl_period,
            z_thresh=params.z_thresh,
            min_points=params.min_points,
        )
        anom_map[col] = anom_df

        anoms_only = anom_df.loc[anom_df["is_anomaly"]].copy()
        if not anoms_only.empty:
            anoms_only["abs_z"] = anoms_only["z"].abs()
            anoms_only = anoms_only.sort_values("abs_z", ascending=False)

        top = []
        for idx, row in anoms_only.head(10).iterrows():
            date_str = pd.Timestamp(idx).date().isoformat() if pd.notna(idx) else ""
            top.append(
                {
                    "date": date_str,
                    "observed": float(row.get("observed", np.nan)) if pd.notna(row.get("observed", np.nan)) else None,
                    "expected": float(row.get("expected", np.nan)) if pd.notna(row.get("expected", np.nan)) else None,
                    "resid": float(row.get("resid", np.nan)) if pd.notna(row.get("resid", np.nan)) else None,
                    "z": float(row.get("z", np.nan)) if pd.notna(row.get("z", np.nan)) else None,
                    "direction": str(row.get("direction", "")),
                }
            )

        by_metric[col] = {
            "n_anomalies": int(anom_df["is_anomaly"].sum()) if "is_anomaly" in anom_df.columns else 0,
            "top": top,
        }

    # Joint score
    joint = {"n_joint_ge_2": 0, "top_joint": []}
    if anom_map:
        idx = next(iter(anom_map.values())).index
        flags = pd.DataFrame(index=idx)
        for metric, frame in anom_map.items():
            flags[metric] = frame.get("is_anomaly", False).astype(int)
        flags = flags.fillna(0).astype(int)

        joint_score = flags.sum(axis=1)
        joint_mask = joint_score >= 2
        joint["n_joint_ge_2"] = int(joint_mask.sum())

        if int(joint_mask.sum()) > 0:
            rows = []
            for dt, score in joint_score.loc[joint_mask].sort_values(ascending=False).head(10).items():
                metrics_hit = [m for m in flags.columns if int(flags.loc[dt, m]) == 1]
                parts = []
                for m in metrics_hit:
                    d = anom_map[m].loc[dt, "direction"] if dt in anom_map[m].index else ""
                    if d:
                        parts.append(f"{m}: {d}")
                    else:
                        parts.append(m)
                rows.append(
                    {
                        "date": pd.Timestamp(dt).date().isoformat(),
                        "joint_score": int(score),
                        "metrics": metrics_hit,
                        "summary": "; ".join(parts),
                    }
                )
            joint["top_joint"] = rows

    return {
        "params": {
            "method": params.method,
            "z_thresh": params.z_thresh,
            "stl_period": params.stl_period,
            "basis": params.basis,
        },
        "by_metric": by_metric,
        "joint": joint,
        "_anom_map": anom_map,
    }
