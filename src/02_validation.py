"""
02_validation.py — manual-validation precision summary.

Purpose
    Stage 2 (independent of the spatial pipeline). Summarizes a manual-validation
    label table into row-level and (if counts are present) object-level
    false-positive rates, with per-device and per-cause breakdowns. This
    characterizes detection PRECISION only; it does not estimate recall.

Inputs
    config['input']['validation_path'] : CSV with columns
        pointId, recordDate, device_name, manual_label
        [false_positive_type] (optional), [totalTrashCount] (optional)
    manual_label values: "true_litter" (valid) vs anything else -> false positive.
    If validation_path is empty, this stage is skipped.

Outputs
    {tables_dir}/validation_summary.csv   (overall + per-device + per-cause rows)

Key parameters
    none (pure tabulation).

Run order
    Independent; can run any time after input is available.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import utils

VALID_LABEL = "true_litter"


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    """Return a tidy summary table: overall, per-device, per-cause."""
    df = df.copy()
    df["is_fp"] = df["manual_label"].astype(str) != VALID_LABEL
    has_counts = "totalTrashCount" in df.columns
    if has_counts:
        df["totalTrashCount"] = pd.to_numeric(df["totalTrashCount"], errors="coerce").fillna(0)

    rows = []

    def block(scope, name, sub):
        n = len(sub)
        n_fp = int(sub["is_fp"].sum())
        row = {"scope": scope, "name": name, "n_records": n,
               "n_false_positive": n_fp,
               "row_fp_rate_pct": round(100 * n_fp / n, 4) if n else np.nan,
               "row_valid_rate_pct": round(100 * (n - n_fp) / n, 4) if n else np.nan}
        if has_counts:
            tot = float(sub["totalTrashCount"].sum())
            fp_tot = float(sub.loc[sub["is_fp"], "totalTrashCount"].sum())
            row["object_fp_rate_pct"] = round(100 * fp_tot / tot, 4) if tot else np.nan
            row["object_valid_rate_pct"] = round(100 * (tot - fp_tot) / tot, 4) if tot else np.nan
        rows.append(row)

    block("overall", "all", df)
    for dev, sub in df.groupby("device_name"):
        block("device", str(dev), sub)
    if "false_positive_type" in df.columns:
        fp = df[df["is_fp"]]
        for cause, sub in fp.groupby(fp["false_positive_type"].fillna("(unspecified)")):
            rows.append({"scope": "fp_cause", "name": str(cause),
                         "n_records": len(sub), "n_false_positive": len(sub),
                         "row_fp_rate_pct": np.nan, "row_valid_rate_pct": np.nan})
    return pd.DataFrame(rows)


def run(cfg: dict):
    val_path = cfg["input"].get("validation_path", "")
    if not val_path:
        utils.log("STAGE 02 — validation: no validation_path configured; skipped")
        return None
    utils.log("STAGE 02 — manual-validation precision summary")
    src = utils.resolve_path(cfg, val_path)
    if not src.exists():
        utils.log(f"  validation file not found ({src}); skipped")
        return None
    cols = utils.canonical_columns(cfg)
    df = pd.read_csv(src, dtype=str, encoding="utf-8-sig")
    utils.validate_columns(df, [cols["point_id"], cols["record_date"],
                                cols["device"], "manual_label"], table_name=src.name)
    df = df.rename(columns={cols["point_id"]: "pointId", cols["record_date"]: "recordDate",
                            cols["device"]: "device_name"})
    summary = summarize(df)
    out_dir = utils.ensure_dir(utils.resolve_path(cfg, cfg["paths"]["tables_dir"]))
    path = out_dir / "validation_summary.csv"
    summary.to_csv(path, index=False, encoding="utf-8")
    overall = summary[summary["scope"] == "overall"].iloc[0]
    utils.log(f"  {int(overall['n_records'])} records, row-level FP "
              f"{overall['row_fp_rate_pct']}%; wrote {path.name}")
    return path


if __name__ == "__main__":  # pragma: no cover
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    a = ap.parse_args()
    run(utils.load_config(a.config))
