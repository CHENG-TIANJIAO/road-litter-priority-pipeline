"""
06_stability_priority.py — temporal stability and management-priority classes.

Purpose
    Stage 6. (a) Assess period-1 vs period-2 stability of the cell indicators
    (Spearman rank correlation with Fisher-z CIs; top-X% hotspot overlap and
    Jaccard index; persistent / emerging / declining hotspots). (b) Classify
    full-period effective cells into HH / HL / LH / LL using percentile
    thresholds of normalized intensity and recurrence ratio, plus a
    non_effective class. Thresholds are derived from the data (full-period
    effective cells with >= 1 unique event), not hard-coded.

Inputs
    {outputs_dir}/litter_analysis/grid_litter_metrics_{full,period1,period2}.csv  (stage 05)

Outputs
    {outputs_dir}/stability_priority/priority_classification_full_period.csv
    {outputs_dir}/stability_priority/period_hotspot_overlap.csv
    {outputs_dir}/stability_priority/persistent_emerging_declining_hotspots.csv
    {outputs_dir}/stability_priority/stability_summary.txt

Key parameters
    priority.main_percentile (80), priority.sensitivity_percentiles,
    hotspot.top_x_percent ([5,10,20]).

Run order
    Last analytical stage. Outputs feed the main tables/figures.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import utils

try:
    from scipy.stats import spearmanr
    _SCIPY = True
except Exception:  # pragma: no cover
    _SCIPY = False


def fisher_z_ci(rho: float, n: int, alpha: float = 0.05):
    """Approximate two-sided CI for a correlation via Fisher z. Descriptive."""
    if n is None or n < 4 or rho is None or not np.isfinite(rho) or abs(rho) >= 1:
        return (np.nan, np.nan)
    z = np.arctanh(rho)
    se = 1.0 / np.sqrt(n - 3)
    # 1.959963985 ~ z_{0.975}
    zc = 1.959963984540054
    lo, hi = z - zc * se, z + zc * se
    return (float(np.tanh(lo)), float(np.tanh(hi)))


def spearman(x: np.ndarray, y: np.ndarray):
    """Return (rho, p). Falls back to a numpy rank correlation if scipy absent."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.size < 3:
        return (np.nan, np.nan)
    if _SCIPY:
        r = spearmanr(x, y)
        return (float(r.correlation), float(r.pvalue))
    rx = pd.Series(x).rank().to_numpy()
    ry = pd.Series(y).rank().to_numpy()
    rho = float(np.corrcoef(rx, ry)[0, 1])
    return (rho, np.nan)


def classify_priority(intensity: np.ndarray, recurrence: np.ndarray,
                      t_int: float, t_rec: float) -> np.ndarray:
    """Quadrant labels HH/HL/LH/LL from intensity/recurrence vs thresholds."""
    intensity = np.asarray(intensity, dtype=float)
    recurrence = np.asarray(recurrence, dtype=float)
    hi_i = intensity >= t_int
    hi_r = recurrence >= t_rec
    out = np.empty(intensity.shape, dtype=object)
    out[hi_i & hi_r] = "HH"
    out[hi_i & ~hi_r] = "HL"
    out[~hi_i & hi_r] = "LH"
    out[~hi_i & ~hi_r] = "LL"
    return out


def top_set(df_eff: pd.DataFrame, x_pct: float):
    """Return (threshold, set_of_grid_ids) for the top-X% by intensity."""
    vals = df_eff["normalized_intensity_per_km"].to_numpy(dtype=float)
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return (np.nan, set())
    thr = float(np.percentile(vals, 100 - x_pct))
    ids = set(df_eff.loc[df_eff["normalized_intensity_per_km"] > thr, "grid_id"])
    return (thr, ids)


def effective_metrics(m: pd.DataFrame) -> pd.DataFrame:
    return m[m["metric_status"] == "effective"].copy()


def run(cfg: dict) -> dict:
    utils.log("STAGE 06 — stability & management priority")
    lit_dir = utils.resolve_path(cfg, cfg["paths"]["outputs_dir"]) / "litter_analysis"
    out_dir = utils.ensure_dir(utils.resolve_path(cfg, cfg["paths"]["outputs_dir"]) / "stability_priority")
    main_pct = cfg["priority"]["main_percentile"]
    sens_pcts = cfg["priority"]["sensitivity_percentiles"]
    top_x = cfg["hotspot"]["top_x_percent"]

    full = pd.read_csv(lit_dir / "grid_litter_metrics_full.csv")
    p1 = pd.read_csv(lit_dir / "grid_litter_metrics_period1.csv")
    p2 = pd.read_csv(lit_dir / "grid_litter_metrics_period2.csv")

    # ---- (a) PRIORITY CLASSIFICATION (full period) -----------------------
    eff_full = effective_metrics(full)
    detected = eff_full[eff_full["n_unique_litter_events"] >= 1]
    if not detected.empty:
        t_int = float(np.percentile(detected["normalized_intensity_per_km"].dropna(), main_pct))
        t_rec = float(np.percentile(detected["recurrence_ratio"].dropna(), main_pct))
    else:
        t_int = t_rec = np.nan

    full = full.copy()
    full["priority_class"] = "non_effective"
    eff_mask = full["metric_status"] == "effective"
    full.loc[eff_mask, "priority_class"] = classify_priority(
        full.loc[eff_mask, "normalized_intensity_per_km"],
        full.loc[eff_mask, "recurrence_ratio"], t_int, t_rec)
    full["intensity_threshold_p%d" % main_pct] = t_int
    full["recurrence_threshold_p%d" % main_pct] = t_rec
    pri_path = out_dir / "priority_classification_full_period.csv"
    full.to_csv(pri_path, index=False, encoding="utf-8")

    counts = full["priority_class"].value_counts().to_dict()
    utils.log("  priority counts: " + ", ".join(
        f"{k}={int(counts.get(k, 0))}" for k in ["HH", "HL", "LH", "LL", "non_effective"]))

    # sensitivity table
    sens_rows = []
    for pct in sens_pcts:
        if detected.empty:
            sens_rows.append({"percentile": pct, "t_intensity": np.nan, "t_recurrence": np.nan})
            continue
        ti = float(np.percentile(detected["normalized_intensity_per_km"].dropna(), pct))
        tr = float(np.percentile(detected["recurrence_ratio"].dropna(), pct))
        cls = classify_priority(eff_full["normalized_intensity_per_km"],
                                eff_full["recurrence_ratio"], ti, tr)
        c = pd.Series(cls).value_counts().to_dict()
        sens_rows.append({"percentile": pct, "t_intensity": ti, "t_recurrence": tr,
                          "HH": c.get("HH", 0), "HL": c.get("HL", 0),
                          "LH": c.get("LH", 0), "LL": c.get("LL", 0)})

    # ---- (b) STABILITY (period1 vs period2) ------------------------------
    e1, e2 = effective_metrics(p1), effective_metrics(p2)
    joined = e1.merge(e2, on="grid_id", how="inner", suffixes=("_p1", "_p2"))
    n_join = len(joined)

    stab = {}
    for metric in ["normalized_intensity_per_km", "recurrence_ratio"]:
        if n_join >= 3:
            rho, p = spearman(joined[f"{metric}_p1"], joined[f"{metric}_p2"])
            lo, hi = fisher_z_ci(rho, n_join)
        else:
            rho = p = lo = hi = np.nan
        stab[metric] = dict(rho=rho, p=p, ci_lo=lo, ci_hi=hi)

    # top-X% overlap
    overlap_rows = []
    joined_ids = set(joined["grid_id"])
    for x in top_x:
        thr1, top1 = top_set(e1, x)
        thr2, top2 = top_set(e2, x)
        t1j, t2j = top1 & joined_ids, top2 & joined_ids
        inter, union = t1j & t2j, t1j | t2j
        jac = (len(inter) / len(union)) if union else np.nan
        overlap_rows.append({"top_x_pct": x, "threshold_p1": thr1, "threshold_p2": thr2,
                             "n_top_p1_joined": len(t1j), "n_top_p2_joined": len(t2j),
                             "n_intersection": len(inter), "jaccard": jac})
    overlap_df = pd.DataFrame(overlap_rows)
    overlap_df.to_csv(out_dir / "period_hotspot_overlap.csv", index=False, encoding="utf-8")

    # persistent / emerging / declining (top-10% / top-20% gates)
    _, top10_p1 = top_set(e1, 10)
    _, top10_p2 = top_set(e2, 10)
    _, top20_p1 = top_set(e1, 20)
    _, top20_p2 = top_set(e2, 20)
    top10_p1 &= joined_ids; top10_p2 &= joined_ids
    top20_p1 &= joined_ids; top20_p2 &= joined_ids
    persistent = top10_p1 & top10_p2
    emerging = (joined_ids - top20_p1) & top10_p2
    declining = top10_p1 & (joined_ids - top20_p2)
    ped_rows = ([{"grid_id": g, "category": "persistent"} for g in sorted(persistent)]
                + [{"grid_id": g, "category": "emerging"} for g in sorted(emerging)]
                + [{"grid_id": g, "category": "declining"} for g in sorted(declining)])
    pd.DataFrame(ped_rows, columns=["grid_id", "category"]).to_csv(
        out_dir / "persistent_emerging_declining_hotspots.csv", index=False, encoding="utf-8")

    # summary.txt
    lines = ["Stage 06 — stability & management priority", "=" * 50,
             f"Priority thresholds (p{main_pct}, full-period detected effective cells):",
             f"  intensity threshold = {t_int:.4f}",
             f"  recurrence threshold = {t_rec:.4f}",
             "Priority class counts (full period):"]
    for k in ["HH", "HL", "LH", "LL", "non_effective"]:
        lines.append(f"  {k:<14} {int(counts.get(k, 0))}")
    lines += ["", f"Stability (period1 vs period2), joined effective cells N = {n_join}:"]
    for metric, s in stab.items():
        lines.append(f"  Spearman rho [{metric}] = {s['rho']:.4f} "
                     f"(95% CI {s['ci_lo']:.3f}..{s['ci_hi']:.3f}, p={s['p']})")
    lines.append("Top-X% hotspot Jaccard overlap:")
    for r in overlap_rows:
        lines.append(f"  top-{r['top_x_pct']}%  Jaccard = {r['jaccard']}")
    lines.append(f"persistent={len(persistent)}  emerging={len(emerging)}  declining={len(declining)}")
    lines += ["", "Priority percentile sensitivity:"]
    for r in sens_rows:
        lines.append("  " + ", ".join(f"{k}={v}" for k, v in r.items()))
    (out_dir / "stability_summary.txt").write_text("\n".join(lines), encoding="utf-8")
    utils.log(f"  wrote {pri_path.name}, period_hotspot_overlap.csv, "
              f"persistent_emerging_declining_hotspots.csv, stability_summary.txt")

    return {"priority": pri_path, "overlap": out_dir / "period_hotspot_overlap.csv"}


if __name__ == "__main__":  # pragma: no cover
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    a = ap.parse_args()
    run(utils.load_config(a.config))
