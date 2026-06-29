"""
05_indicators.py — exposure-normalized intensity and recurrence ratio.

Purpose
    Stage 5. Join the per-cell observation exposure (stage 03) with the unique
    litter events (stage 04) and the raw detection-day counts, and compute the
    two cell-level indicators:
        normalized_intensity_per_km = n_unique_litter_events / valid_distance_km
        recurrence_ratio            = n_detection_days / n_observation_days
    Formal (non-missing) values are produced only for effective cells with
    valid_distance_km > 0; other cells are kept but labelled.

Inputs
    {outputs_dir}/grid_analysis/grid_exposure_{label}.csv        (stage 03)
    {outputs_dir}/litter_analysis/unique_litter_events_{label}.csv (stage 04)
    {outputs_dir}/processed/all_points_cleaned.csv               (stage 01; for detection-days)

Outputs
    {outputs_dir}/litter_analysis/grid_litter_metrics_{full,period1,period2}.csv

Key parameters
    spatial.grid_size_m (100), spatial.effective_observation_days_min (5).

Run order
    After 03 and 04. Consumed by 06 (stability/priority).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import utils

METRIC_COLUMNS = [
    "grid_id", "cell_ix", "cell_iy", "lon_center", "lat_center",
    "n_observation_points", "n_observation_days", "n_devices_observed",
    "valid_distance_m", "valid_distance_km", "is_effective_coverage",
    "n_unique_litter_events", "n_detection_days",
    "normalized_intensity_per_km", "recurrence_ratio",
    "metric_status", "period_label", "period_start", "period_end",
]


def normalized_intensity(n_events, valid_distance_km):
    """events per valid km; NaN where valid_distance_km <= 0."""
    n_events = np.asarray(n_events, dtype=float)
    vk = np.asarray(valid_distance_km, dtype=float)
    out = np.full(n_events.shape, np.nan)
    ok = vk > 0
    out[ok] = n_events[ok] / vk[ok]
    return out


def recurrence_ratio(n_detection_days, n_observation_days):
    """detection days / observation days in [0, 1]; NaN where obs days <= 0."""
    d = np.asarray(n_detection_days, dtype=float)
    o = np.asarray(n_observation_days, dtype=float)
    out = np.full(d.shape, np.nan)
    ok = o > 0
    out[ok] = d[ok] / o[ok]
    return out


def detection_days_per_cell(points_csv: Path, grid_size_m: float,
                            start: str, end: str) -> pd.DataFrame:
    """n_detection_days per cell from RAW detection rows (distinct dates)."""
    df = pd.read_csv(points_csv, low_memory=False)
    df["date_ts"] = pd.to_datetime(df["date_ts"], errors="coerce")
    df["is_detection"] = df["is_detection"].astype(bool)
    df = df[df["is_detection"] & df["x_m"].notna() & df["y_m"].notna()].copy()
    df = df.loc[utils.period_mask(df["date_ts"], start, end)]
    if df.empty:
        return pd.DataFrame(columns=["grid_id", "n_detection_days"])
    df["cell_ix"], df["cell_iy"] = utils.cell_indices(df["x_m"], df["y_m"], grid_size_m)
    df["grid_id"] = utils.grid_id(df["cell_ix"], df["cell_iy"]).to_numpy()
    df["date_only"] = df["date_ts"].dt.normalize()
    g = df.groupby("grid_id")["date_only"].nunique().reset_index()
    g.columns = ["grid_id", "n_detection_days"]
    return g


def build_metrics(exposure: pd.DataFrame, events: pd.DataFrame,
                  det_days: pd.DataFrame, eff_days_min: int) -> pd.DataFrame:
    """Merge exposure + event counts + detection days; compute indicators."""
    ev = (events.groupby("grid_id").size().reset_index(name="n_unique_litter_events")
          if not events.empty else pd.DataFrame(columns=["grid_id", "n_unique_litter_events"]))
    m = exposure.merge(ev, on="grid_id", how="left").merge(det_days, on="grid_id", how="left")
    m["n_unique_litter_events"] = m["n_unique_litter_events"].fillna(0).astype(np.int64)
    m["n_detection_days"] = m["n_detection_days"].fillna(0).astype(np.int64)

    m["normalized_intensity_per_km"] = normalized_intensity(
        m["n_unique_litter_events"], m["valid_distance_km"])
    m["recurrence_ratio"] = recurrence_ratio(
        m["n_detection_days"], m["n_observation_days"])

    eff = m["n_observation_days"] >= eff_days_min
    status = np.where(~eff, "not_effective",
                      np.where(m["valid_distance_km"] > 0, "effective", "div_zero"))
    m["metric_status"] = status
    # blank formal indicators outside the effective+valid set
    blank = m["metric_status"] != "effective"
    m.loc[blank, "normalized_intensity_per_km"] = np.nan
    return m


def run(cfg: dict) -> dict:
    utils.log("STAGE 05 — intensity & recurrence indicators")
    grid_size_m = cfg["spatial"]["grid_size_m"]
    eff_min = cfg["spatial"]["effective_observation_days_min"]
    out_root = utils.resolve_path(cfg, cfg["paths"]["outputs_dir"])
    points_csv = out_root / "processed" / "all_points_cleaned.csv"
    grid_dir = out_root / "grid_analysis"
    lit_dir = utils.ensure_dir(out_root / "litter_analysis")

    written = {}
    for label, start, end in utils.iter_periods(cfg):
        exp = pd.read_csv(grid_dir / f"grid_exposure_{label}.csv")
        ev_path = lit_dir / f"unique_litter_events_{label}.csv"
        ev = pd.read_csv(ev_path) if ev_path.exists() else pd.DataFrame(columns=["grid_id"])
        dd = detection_days_per_cell(points_csv, grid_size_m, start, end)
        m = build_metrics(exp, ev, dd, eff_min)
        for c in ["period_label", "period_start", "period_end"]:
            m[c] = exp[c].iloc[0] if (c in exp.columns and not exp.empty) else {"period_label": label, "period_start": start, "period_end": end}[c]
        m = m[METRIC_COLUMNS]
        path = lit_dir / f"grid_litter_metrics_{label}.csv"
        m.to_csv(path, index=False, encoding="utf-8")
        n_eff = int((m["metric_status"] == "effective").sum())
        utils.log(f"  {label}: {len(m):,} cells ({n_eff} effective); "
                  f"sum events={int(m['n_unique_litter_events'].sum()):,}; wrote {path.name}")
        written[label] = path
    return written


if __name__ == "__main__":  # pragma: no cover
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    a = ap.parse_args()
    run(utils.load_config(a.config))
