"""
make_main_tables.py — build the manuscript main tables from pipeline outputs.

Usage
    python scripts/make_main_tables.py --config config/example_config.yaml

Reads the stage 03/05/06 outputs (and validation_summary.csv if present) and
writes compact, reproducible CSV versions of:
    table1_study_data_exposure.csv
    table2_validation.csv            (only if validation_summary.csv exists)
    table3_stability_priority.csv
into {tables_dir}. These are derived purely from the analytical outputs, so the
same script reproduces the synthetic-example tables or (with the real, restricted
inputs) the manuscript tables.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
import utils  # noqa: E402


def table1_study_data_exposure(out_root: Path) -> pd.DataFrame:
    grid_dir = out_root / "grid_analysis"
    lit_dir = out_root / "litter_analysis"
    rows = []
    for label in ["full", "period1", "period2"]:
        exp = pd.read_csv(grid_dir / f"grid_exposure_{label}.csv")
        met = pd.read_csv(lit_dir / f"grid_litter_metrics_{label}.csv")
        rows.append({
            "period": label,
            "period_start": exp["period_start"].iloc[0] if len(exp) else "",
            "period_end": exp["period_end"].iloc[0] if len(exp) else "",
            "n_cells": len(exp),
            "n_effective_cells": int(exp["is_effective_coverage"].sum()) if len(exp) else 0,
            "sum_observation_points": int(exp["n_observation_points"].sum()) if len(exp) else 0,
            "sum_valid_distance_km": round(float(exp["valid_distance_km"].sum()), 3) if len(exp) else 0.0,
            "sum_raw_detection_rows": int(exp["n_detection_rows_raw"].sum()) if len(exp) else 0,
            "sum_unique_litter_events": int(met["n_unique_litter_events"].sum()) if len(met) else 0,
        })
    return pd.DataFrame(rows)


def table3_stability_priority(out_root: Path) -> pd.DataFrame:
    sp = out_root / "stability_priority"
    pri = pd.read_csv(sp / "priority_classification_full_period.csv")
    counts = pri["priority_class"].value_counts().to_dict()
    overlap = pd.read_csv(sp / "period_hotspot_overlap.csv")
    rows = []
    for k in ["HH", "HL", "LH", "LL", "non_effective"]:
        rows.append({"metric": f"priority_{k}_cells", "value": int(counts.get(k, 0))})
    ti = [c for c in pri.columns if c.startswith("intensity_threshold_p")]
    tr = [c for c in pri.columns if c.startswith("recurrence_threshold_p")]
    if ti:
        rows.append({"metric": ti[0], "value": round(float(pri[ti[0]].iloc[0]), 4)})
    if tr:
        rows.append({"metric": tr[0], "value": round(float(pri[tr[0]].iloc[0]), 4)})
    for _, r in overlap.iterrows():
        rows.append({"metric": f"jaccard_top{int(r['top_x_pct'])}pct",
                     "value": round(float(r["jaccard"]), 4) if pd.notna(r["jaccard"]) else ""})
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    a = ap.parse_args()
    cfg = utils.load_config(a.config)
    out_root = utils.resolve_path(cfg, cfg["paths"]["outputs_dir"])
    tab_dir = utils.ensure_dir(utils.resolve_path(cfg, cfg["paths"]["tables_dir"]))

    t1 = table1_study_data_exposure(out_root)
    t1.to_csv(tab_dir / "table1_study_data_exposure.csv", index=False, encoding="utf-8")
    utils.log(f"wrote table1_study_data_exposure.csv ({len(t1)} rows)")

    val = tab_dir / "validation_summary.csv"
    if val.exists():
        pd.read_csv(val).to_csv(tab_dir / "table2_validation.csv", index=False, encoding="utf-8")
        utils.log("wrote table2_validation.csv")
    else:
        utils.log("validation_summary.csv not found; table2_validation.csv skipped")

    t3 = table3_stability_priority(out_root)
    t3.to_csv(tab_dir / "table3_stability_priority.csv", index=False, encoding="utf-8")
    utils.log(f"wrote table3_stability_priority.csv ({len(t3)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
