"""
make_main_figures.py — reproduce the manuscript main figures from outputs.

Usage
    python scripts/make_main_figures.py --config config/example_config.yaml

Produces (300 DPI PNG) into {figures_dir}:
    fig_observation_coverage.png      — n_observation_days per cell (full period)
    fig_normalized_intensity.png      — normalized_intensity_per_km (effective cells)
    fig_recurrence_ratio.png          — recurrence_ratio (effective cells)
    fig_period_stability.png          — period-1 vs period-2 intensity scatter
    fig_priority_classification.png   — HH/HL/LH/LL/non-effective map

These are clean, reproducible renderings driven entirely by the pipeline
outputs; the publication-polished figures in the paper share the same data.
Font is Times New Roman where available (matches the manuscript).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams, font_manager
from matplotlib.collections import PatchCollection
from matplotlib.patches import Rectangle

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
import utils  # noqa: E402

PRIORITY_COLORS = {"HH": "#d73027", "HL": "#fc8d59", "LH": "#4575b4",
                   "LL": "#fee090", "non_effective": "#dddddd"}


def setup_font():
    have = {f.name for f in font_manager.fontManager.ttflist}
    rcParams["font.family"] = "Times New Roman" if "Times New Roman" in have else "DejaVu Serif"
    rcParams["axes.unicode_minus"] = False


def _cell_map(df, value_col, title, cbar_label, outpath, grid_size_m,
              categorical=None):
    setup_font()
    fig, ax = plt.subplots(figsize=(8, 8))
    rects = [Rectangle((ix * grid_size_m, iy * grid_size_m), grid_size_m, grid_size_m)
             for ix, iy in zip(df["cell_ix"], df["cell_iy"])]
    if categorical:
        colors = [PRIORITY_COLORS.get(c, "#999999") for c in df[value_col]]
        pc = PatchCollection(rects, facecolor=colors, edgecolor="none")
        ax.add_collection(pc)
        handles = [plt.Line2D([0], [0], marker="s", linestyle="", markersize=10,
                              markerfacecolor=PRIORITY_COLORS[k], markeredgecolor="none",
                              label=k) for k in PRIORITY_COLORS]
        ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.01, 0.5),
                  frameon=True, title="Priority class")
    else:
        vals = df[value_col].to_numpy(dtype=float)
        pos = vals[np.isfinite(vals) & (vals > 0)]
        vmax = float(np.percentile(pos, 95)) if pos.size else 1.0
        pc = PatchCollection(rects, cmap="viridis", edgecolor="none")
        pc.set_array(np.nan_to_num(vals)); pc.set_clim(0, vmax)
        ax.add_collection(pc)
        cb = plt.colorbar(pc, ax=ax, shrink=0.75)
        cb.set_label(cbar_label)
    ax.set_aspect("equal")
    xs = df["cell_ix"].to_numpy() * grid_size_m
    ys = df["cell_iy"].to_numpy() * grid_size_m
    pad = grid_size_m * 2
    ax.set_xlim(xs.min() - pad, xs.max() + 2 * grid_size_m + pad)
    ax.set_ylim(ys.min() - pad, ys.max() + 2 * grid_size_m + pad)
    ax.set_xlabel("Projected X (m)"); ax.set_ylabel("Projected Y (m)")
    ax.set_title(title)
    plt.tight_layout()
    plt.savefig(outpath, dpi=300, bbox_inches="tight")
    plt.close()
    utils.log(f"  wrote {outpath.name}")


def fig_stability(p1, p2, outpath):
    setup_font()
    e1 = p1[p1["metric_status"] == "effective"][["grid_id", "normalized_intensity_per_km"]]
    e2 = p2[p2["metric_status"] == "effective"][["grid_id", "normalized_intensity_per_km"]]
    j = e1.merge(e2, on="grid_id", suffixes=("_p1", "_p2")).dropna()
    fig, ax = plt.subplots(figsize=(7, 7))
    if len(j):
        ax.scatter(j["normalized_intensity_per_km_p1"], j["normalized_intensity_per_km_p2"],
                   s=18, c="#888888", edgecolors="none")
        m = max(j["normalized_intensity_per_km_p1"].max(), j["normalized_intensity_per_km_p2"].max()) * 1.05
        lo = -0.03 * m
        ax.plot([0, m], [0, m], "--", color="#999999", lw=0.8)
        ax.set_xlim(lo, m); ax.set_ylim(lo, m)
    ax.set_xlabel(r"Period 1 normalized litter intensity (events km$^{-1}$)")
    ax.set_ylabel(r"Period 2 normalized litter intensity (events km$^{-1}$)")
    ax.set_title("Period stability")
    plt.tight_layout(); plt.savefig(outpath, dpi=300, bbox_inches="tight"); plt.close()
    utils.log(f"  wrote {outpath.name}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    a = ap.parse_args()
    cfg = utils.load_config(a.config)
    gsm = cfg["spatial"]["grid_size_m"]
    out_root = utils.resolve_path(cfg, cfg["paths"]["outputs_dir"])
    fig_dir = utils.ensure_dir(utils.resolve_path(cfg, cfg["paths"]["figures_dir"]))

    exp = pd.read_csv(out_root / "grid_analysis" / "grid_exposure_full.csv")
    met = pd.read_csv(out_root / "litter_analysis" / "grid_litter_metrics_full.csv")
    pri = pd.read_csv(out_root / "stability_priority" / "priority_classification_full_period.csv")
    p1 = pd.read_csv(out_root / "litter_analysis" / "grid_litter_metrics_period1.csv")
    p2 = pd.read_csv(out_root / "litter_analysis" / "grid_litter_metrics_period2.csv")

    utils.log("STAGE — main figures")
    _cell_map(exp, "n_observation_days", "Observation coverage (full period)",
              "Observation days per 100 m cell", fig_dir / "fig_observation_coverage.png", gsm)
    eff = met[met["metric_status"] == "effective"]
    _cell_map(eff, "normalized_intensity_per_km", "Normalized litter intensity",
              "Unique events per valid km", fig_dir / "fig_normalized_intensity.png", gsm)
    _cell_map(eff, "recurrence_ratio", "Recurrence ratio",
              "Detection days / observation days", fig_dir / "fig_recurrence_ratio.png", gsm)
    _cell_map(pri, "priority_class", "Management-priority classification", None,
              fig_dir / "fig_priority_classification.png", gsm, categorical="priority_class")
    fig_stability(p1, p2, fig_dir / "fig_period_stability.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
