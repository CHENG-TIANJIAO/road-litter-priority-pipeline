"""
01_inventory.py — merge, quality control and trajectory speed flags.

Purpose
    Stage 1 of the pipeline. Reads point-level detection records (public input
    schema), merges multiple files if a directory is given, parses timestamps,
    projects WGS84 lon/lat to the metric CRS, computes per-device inter-point
    distance / time / speed, and assigns exactly one speed quality flag per row.
    No row is ever deleted because of a flag; flags only control which segments
    contribute to "valid driving distance" downstream.

Inputs
    config['input']['points_path'] : CSV file or directory of CSVs with columns
        (names configurable in config['columns']):
        pointId, recordDate, latitude, longitude, device_name, totalTrashCount

Outputs
    {outputs_dir}/processed/all_points_cleaned.csv
        original columns + date_ts, is_detection, x_m, y_m, dist_m, dt_sec,
        speed_kmh, speed_flag, device_short, source_file

Key parameters
    quality_control.speed_abnormal_kmh (120), gps_jump_dist_m (1000),
    gps_jump_dt_sec (60); crs.geographic/projected.

Run order
    First. Produces the cleaned point table consumed by stages 03 and 04.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import utils

SPEED_FLAGS = ["first_row", "dt_nonpositive", "gps_jump", "abnormal_high", "ok"]


# --------------------------------------------------------------------------- #
# Pure functions (unit-testable)
# --------------------------------------------------------------------------- #
def assign_speed_flag(is_first: pd.Series, dt_sec: pd.Series,
                      dist_m: pd.Series, speed_kmh: pd.Series,
                      abnormal_kmh: float, jump_dist_m: float,
                      jump_dt_sec: float) -> pd.Series:
    """Assign exactly one speed_flag per row, fixed priority (highest wins):
    first_row > dt_nonpositive > gps_jump > abnormal_high > ok."""
    flag = pd.Series("ok", index=dt_sec.index, dtype="object")
    flag.loc[(speed_kmh > abnormal_kmh).fillna(False)] = "abnormal_high"
    flag.loc[((dist_m > jump_dist_m) & (dt_sec < jump_dt_sec)).fillna(False)] = "gps_jump"
    flag.loc[(dt_sec <= 0).fillna(False)] = "dt_nonpositive"
    flag.loc[is_first.fillna(False)] = "first_row"
    return flag


def compute_trajectory_metrics(df: pd.DataFrame, qc: dict) -> pd.DataFrame:
    """Add date_ts, is_detection, dist_m, dt_sec, speed_kmh, speed_flag.

    Requires columns x_m, y_m, date_ts, totalTrashCount, device_name.
    Inter-point metrics are computed within each device, ordered by time.
    """
    df = df.sort_values(["device_name", "date_ts"], kind="mergesort").reset_index(drop=True)
    df["is_detection"] = df["totalTrashCount"].fillna(0) > 0

    # per-device previous point
    grp = df.groupby("device_name", sort=False)
    prev_x = grp["x_m"].shift(1)
    prev_y = grp["y_m"].shift(1)
    prev_t = grp["date_ts"].shift(1)
    is_first = prev_t.isna()

    dx = df["x_m"] - prev_x
    dy = df["y_m"] - prev_y
    dist_m = np.sqrt(dx * dx + dy * dy)
    dt_sec = (df["date_ts"] - prev_t).dt.total_seconds()
    with np.errstate(divide="ignore", invalid="ignore"):
        speed_kmh = (dist_m / dt_sec) * 3.6

    df["dist_m"] = dist_m
    df["dt_sec"] = dt_sec
    df["speed_kmh"] = speed_kmh
    df["speed_flag"] = assign_speed_flag(
        is_first, dt_sec, dist_m, speed_kmh,
        abnormal_kmh=qc["speed_abnormal_kmh"],
        jump_dist_m=qc["gps_jump_dist_m"],
        jump_dt_sec=qc["gps_jump_dt_sec"],
    )
    # speed undefined for first_row / dt_nonpositive
    df.loc[df["speed_flag"].isin(["first_row", "dt_nonpositive"]), "speed_kmh"] = np.nan
    return df


# --------------------------------------------------------------------------- #
# IO
# --------------------------------------------------------------------------- #
def read_points(cfg: dict) -> pd.DataFrame:
    """Read the point table(s) and rename configured columns to canonical names.

    Only the six canonical columns are kept; any extra columns in the source
    (e.g. image URLs / capture IDs in the restricted raw data) are dropped and
    are never required.
    """
    cols = utils.canonical_columns(cfg)
    src = utils.resolve_path(cfg, cfg["input"]["points_path"])
    if src.is_dir():
        files = sorted(src.glob("*.csv"))
        if not files:
            raise FileNotFoundError(f"No CSV files found in input directory: {src}")
    elif src.exists():
        files = [src]
    else:
        raise FileNotFoundError(f"Input points_path does not exist: {src}")

    frames = []
    for f in files:
        raw = pd.read_csv(f, dtype=str, encoding="utf-8-sig")
        utils.validate_columns(raw, cols.values(), table_name=str(f.name))
        sub = raw[[cols["point_id"], cols["record_date"], cols["latitude"],
                   cols["longitude"], cols["device"], cols["trash_count"]]].copy()
        sub.columns = ["pointId", "recordDate", "latitude", "longitude",
                       "device_name", "totalTrashCount"]
        sub["source_file"] = f.name
        frames.append(sub)
    df = pd.concat(frames, ignore_index=True)
    utils.log(f"  read {len(df):,} rows from {len(files)} file(s)")
    return df


def run(cfg: dict) -> Path:
    utils.log("STAGE 01 — inventory & quality control")
    qc = cfg["quality_control"]
    df = read_points(cfg)

    # types + parsing
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["totalTrashCount"] = pd.to_numeric(df["totalTrashCount"], errors="coerce")
    df["date_ts"] = pd.to_datetime(df["recordDate"], errors="coerce")

    n0 = len(df)
    df = df[df["latitude"].notna() & df["longitude"].notna() & df["date_ts"].notna()].copy()
    utils.log(f"  dropped {n0 - len(df):,} rows with missing coord/time; {len(df):,} usable")

    # QC bounding box (count only, never drop)
    lat_lo, lat_hi = cfg["input"]["qc_bbox_lat"]
    lon_lo, lon_hi = cfg["input"]["qc_bbox_lon"]
    out_box = int((~(df["latitude"].between(lat_lo, lat_hi)
                     & df["longitude"].between(lon_lo, lon_hi))).sum())
    if out_box:
        utils.log(f"  QC WARNING: {out_box:,} rows outside the configured bbox "
                  f"(kept, not dropped)")

    # projection
    fwd, _ = utils.get_transformers(cfg)
    x_m, y_m = fwd.transform(df["longitude"].to_numpy(), df["latitude"].to_numpy())
    df["x_m"] = x_m
    df["y_m"] = y_m

    # trajectory metrics + flags
    df = compute_trajectory_metrics(df, qc)
    df["device_short"] = df["device_name"].astype(str)

    counts = df["speed_flag"].value_counts().to_dict()
    utils.log("  speed_flag counts: "
              + ", ".join(f"{k}={int(counts.get(k, 0)):,}" for k in SPEED_FLAGS))
    utils.log(f"  detection rows (totalTrashCount>0): {int(df['is_detection'].sum()):,}")

    out_dir = utils.ensure_dir(utils.resolve_path(cfg, cfg["paths"]["outputs_dir"]) / "processed")
    out_csv = out_dir / "all_points_cleaned.csv"
    df.to_csv(out_csv, index=False, encoding="utf-8")
    utils.log(f"  wrote {out_csv} ({len(df):,} rows)")
    return out_csv


if __name__ == "__main__":  # pragma: no cover
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    a = ap.parse_args()
    run(utils.load_config(a.config))
