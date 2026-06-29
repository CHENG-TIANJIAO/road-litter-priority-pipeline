"""
03_exposure.py — trajectory-based observation exposure on a 100 m grid.

Purpose
    Stage 3. For each analytical period (full / period1 / period2) aggregate the
    cleaned point table onto a 100 m grid and compute, per cell:
        n_observation_points  — all trajectory rows in the cell
        n_observation_days    — distinct calendar dates observed
        n_devices_observed    — distinct devices
        valid_distance_m/km   — sum of inter-point distance on 'ok' segments only
        is_effective_coverage — n_observation_days >= effective_observation_days_min
    Raw detection references (n_detection_rows_raw, sum_totalTrashCount_raw) are
    carried for cross-checking; formal de-duplicated metrics come from stage 04/05.

Inputs
    {outputs_dir}/processed/all_points_cleaned.csv   (from stage 01)

Outputs
    {outputs_dir}/grid_analysis/grid_exposure_full.csv
    {outputs_dir}/grid_analysis/grid_exposure_period1.csv
    {outputs_dir}/grid_analysis/grid_exposure_period2.csv

Key parameters
    spatial.grid_size_m (100), spatial.effective_observation_days_min (5).

Run order
    After 01. Consumed by 05 (indicators) and 06 (stability/priority).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import utils

EXPOSURE_COLUMNS = [
    "grid_id", "cell_ix", "cell_iy", "x_center_m", "y_center_m",
    "lon_center", "lat_center",
    "n_observation_points", "n_observation_days", "n_devices_observed",
    "n_points_excluded_abnormal_segments",
    "valid_distance_m", "valid_distance_km",
    "n_detection_rows_raw", "sum_totalTrashCount_raw",
    "is_effective_coverage", "period_label", "period_start", "period_end",
]


def aggregate_exposure(sub: pd.DataFrame, grid_size_m: float, eff_days_min: int,
                       inv_transformer, period_label: str,
                       period_start: str, period_end: str) -> pd.DataFrame:
    """Aggregate a period slice (with cell_ix/iy, valid_dist_m, etc.) to cells."""
    if sub.empty:
        return pd.DataFrame(columns=EXPOSURE_COLUMNS)

    g = sub.groupby(["cell_ix", "cell_iy"], sort=False)
    out = g.agg(
        n_observation_points=("pointId", "size"),
        n_observation_days=("date_only", "nunique"),
        n_devices_observed=("device_short", "nunique"),
        n_points_excluded_abnormal_segments=("seg_excluded", "sum"),
        valid_distance_m=("valid_dist_m", "sum"),
        n_detection_rows_raw=("is_detection", "sum"),
        sum_totalTrashCount_raw=("ttc_for_sum", "sum"),
    ).reset_index()

    for c in ["n_observation_points", "n_observation_days", "n_devices_observed",
              "n_points_excluded_abnormal_segments", "n_detection_rows_raw"]:
        out[c] = out[c].astype(np.int64)
    out["valid_distance_m"] = out["valid_distance_m"].astype(float)
    out["sum_totalTrashCount_raw"] = out["sum_totalTrashCount_raw"].astype(float)
    out["valid_distance_km"] = out["valid_distance_m"] / 1000.0

    xc, yc = utils.cell_center_m(out["cell_ix"], out["cell_iy"], grid_size_m)
    out["x_center_m"] = xc
    out["y_center_m"] = yc
    lon_c, lat_c = inv_transformer.transform(xc, yc)
    out["lon_center"] = lon_c
    out["lat_center"] = lat_c
    out["grid_id"] = utils.grid_id(out["cell_ix"], out["cell_iy"]).to_numpy()
    out["is_effective_coverage"] = out["n_observation_days"] >= eff_days_min
    out["period_label"] = period_label
    out["period_start"] = period_start
    out["period_end"] = period_end
    return out[EXPOSURE_COLUMNS].sort_values(["cell_ix", "cell_iy"]).reset_index(drop=True)


def _prep(df: pd.DataFrame, grid_size_m: float) -> pd.DataFrame:
    df = df.copy()
    df["date_ts"] = pd.to_datetime(df["date_ts"], errors="coerce")
    df["date_only"] = df["date_ts"].dt.normalize()
    df["x_m"] = pd.to_numeric(df["x_m"], errors="coerce")
    df["y_m"] = pd.to_numeric(df["y_m"], errors="coerce")
    df = df[df["x_m"].notna() & df["y_m"].notna() & df["date_ts"].notna()].copy()
    df["cell_ix"], df["cell_iy"] = utils.cell_indices(df["x_m"], df["y_m"], grid_size_m)
    is_ok = df["speed_flag"].astype(str).eq("ok")
    df["valid_dist_m"] = np.where(is_ok, pd.to_numeric(df["dist_m"], errors="coerce").fillna(0.0), 0.0)
    df["seg_excluded"] = (~is_ok).astype(np.int64)
    df["is_detection"] = df["is_detection"].astype(bool)
    df["ttc_for_sum"] = np.where(
        df["is_detection"], pd.to_numeric(df["totalTrashCount"], errors="coerce").fillna(0).astype(float), 0.0)
    return df


def run(cfg: dict) -> dict:
    utils.log("STAGE 03 — observation exposure")
    grid_size_m = cfg["spatial"]["grid_size_m"]
    eff_min = cfg["spatial"]["effective_observation_days_min"]
    in_csv = utils.resolve_path(cfg, cfg["paths"]["outputs_dir"]) / "processed" / "all_points_cleaned.csv"
    if not in_csv.exists():
        raise FileNotFoundError(f"{in_csv} not found. Run stage 01 first.")
    df = _prep(pd.read_csv(in_csv, low_memory=False), grid_size_m)
    _, inv = utils.get_transformers(cfg)
    out_dir = utils.ensure_dir(utils.resolve_path(cfg, cfg["paths"]["outputs_dir"]) / "grid_analysis")

    written = {}
    for label, start, end in utils.iter_periods(cfg):
        sub = df.loc[utils.period_mask(df["date_ts"], start, end)]
        grid = aggregate_exposure(sub, grid_size_m, eff_min, inv, label, start, end)
        path = out_dir / f"grid_exposure_{label}.csv"
        grid.to_csv(path, index=False, encoding="utf-8")
        n_eff = int(grid["is_effective_coverage"].sum()) if not grid.empty else 0
        utils.log(f"  {label}: {len(sub):,} rows -> {len(grid):,} cells "
                  f"({n_eff} effective); wrote {path.name}")
        written[label] = path
    return written


if __name__ == "__main__":  # pragma: no cover
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    a = ap.parse_args()
    run(utils.load_config(a.config))
