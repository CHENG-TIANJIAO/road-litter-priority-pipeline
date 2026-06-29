"""
04_deduplication.py — 3 m seed-radius spatial deduplication of detections.

Purpose
    Stage 4. Collapse repeated detections of the same physical litter item into
    "unique litter events". Detection rows are sorted by (recordDate, pointId);
    the first unassigned row becomes a cluster seed, and every still-unassigned
    row within `dedup_radius_m` of that seed joins the cluster. Cluster members
    do NOT seed further growth, so each cluster is bounded by a disk of radius
    `dedup_radius_m` around its seed. This deliberately avoids the chain-like
    over-merging of single-link agglomerative clustering.

Inputs
    {outputs_dir}/processed/all_points_cleaned.csv   (from stage 01)

Outputs
    {outputs_dir}/litter_analysis/unique_litter_events_{full,period1,period2}.csv
        cluster_id, n_member_rows, centroid_x_m, centroid_y_m,
        max_distance_from_seed_m, cell_ix, cell_iy, grid_id, period_label

Key parameters
    spatial.dedup_radius_m (3.0), spatial.grid_size_m (100).

Run order
    After 01. Its event counts feed stage 05 (indicators).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import utils

try:
    from scipy.spatial import cKDTree
    _SCIPY = True
except Exception:  # pragma: no cover
    _SCIPY = False


def seed_radius_clusters(xy: np.ndarray, radius_m: float) -> np.ndarray:
    """Assign seed-radius cluster ids to points given in SEED ORDER.

    `xy` is an (n, 2) array already ordered so that row i is the i-th seed
    candidate. Returns an int array of length n with cluster ids 0..K-1 in seed
    order. Every member lies within `radius_m` of its cluster's seed; membership
    does not propagate outward (no single-link chaining).
    """
    n = xy.shape[0]
    cluster = np.full(n, -1, dtype=np.int64)
    if n == 0:
        return cluster
    if _SCIPY:
        tree = cKDTree(xy)
        next_cid = 0
        for k in range(n):
            if cluster[k] != -1:
                continue
            neigh = tree.query_ball_point(xy[k], r=radius_m)
            for j in neigh:
                if cluster[j] == -1:
                    cluster[j] = next_cid
            next_cid += 1
    else:  # pragma: no cover - pure-numpy fallback (O(n^2))
        next_cid = 0
        for k in range(n):
            if cluster[k] != -1:
                continue
            d2 = ((xy - xy[k]) ** 2).sum(axis=1)
            within = np.where(d2 <= radius_m * radius_m)[0]
            for j in within:
                if cluster[j] == -1:
                    cluster[j] = next_cid
            next_cid += 1
    return cluster


def cluster_table(detections: pd.DataFrame, radius_m: float,
                  grid_size_m: float) -> pd.DataFrame:
    """Deduplicate detection rows -> one row per unique litter event (cluster).

    `detections` must have columns: pointId, recordDate, x_m, y_m.
    """
    if detections.empty:
        return pd.DataFrame(columns=[
            "cluster_id", "n_member_rows", "centroid_x_m", "centroid_y_m",
            "max_distance_from_seed_m", "cell_ix", "cell_iy", "grid_id"])
    s = detections.sort_values(["recordDate", "pointId"], kind="mergesort").reset_index(drop=True)
    xy = s[["x_m", "y_m"]].to_numpy(dtype=float)
    s["cluster_id"] = seed_radius_clusters(xy, radius_m)

    # seed coordinate per cluster = first row (seed order preserved by sort)
    seed_xy = s.groupby("cluster_id", sort=True)[["x_m", "y_m"]].first()
    g = s.groupby("cluster_id", sort=True)
    out = g.agg(n_member_rows=("pointId", "size"),
                centroid_x_m=("x_m", "mean"),
                centroid_y_m=("y_m", "mean")).reset_index()
    # max member-to-seed distance (bounded by radius_m by construction)
    sx = seed_xy["x_m"].to_numpy()[s["cluster_id"].to_numpy()]
    sy = seed_xy["y_m"].to_numpy()[s["cluster_id"].to_numpy()]
    s["_d_seed"] = np.sqrt((s["x_m"] - sx) ** 2 + (s["y_m"] - sy) ** 2)
    out["max_distance_from_seed_m"] = g["_d_seed"].max().to_numpy()

    out["cell_ix"], out["cell_iy"] = utils.cell_indices(
        out["centroid_x_m"], out["centroid_y_m"], grid_size_m)
    out["grid_id"] = utils.grid_id(out["cell_ix"], out["cell_iy"]).to_numpy()
    return out


def run(cfg: dict) -> dict:
    utils.log("STAGE 04 — 3 m seed-radius deduplication")
    radius_m = cfg["spatial"]["dedup_radius_m"]
    grid_size_m = cfg["spatial"]["grid_size_m"]
    in_csv = utils.resolve_path(cfg, cfg["paths"]["outputs_dir"]) / "processed" / "all_points_cleaned.csv"
    if not in_csv.exists():
        raise FileNotFoundError(f"{in_csv} not found. Run stage 01 first.")
    df = pd.read_csv(in_csv, low_memory=False)
    df["date_ts"] = pd.to_datetime(df["date_ts"], errors="coerce")
    df["is_detection"] = df["is_detection"].astype(bool)
    det = df[df["is_detection"] & df["x_m"].notna() & df["y_m"].notna()].copy()

    out_dir = utils.ensure_dir(utils.resolve_path(cfg, cfg["paths"]["outputs_dir"]) / "litter_analysis")
    written = {}
    for label, start, end in utils.iter_periods(cfg):
        sub = det.loc[utils.period_mask(det["date_ts"], start, end)]
        tbl = cluster_table(sub, radius_m, grid_size_m)
        tbl["period_label"] = label
        path = out_dir / f"unique_litter_events_{label}.csv"
        tbl.to_csv(path, index=False, encoding="utf-8")
        utils.log(f"  {label}: {len(sub):,} detection rows -> "
                  f"{len(tbl):,} unique events; wrote {path.name}")
        written[label] = path
    return written


if __name__ == "__main__":  # pragma: no cover
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    a = ap.parse_args()
    run(utils.load_config(a.config))
