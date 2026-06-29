"""
run_pipeline.py — orchestrate the full post-detection pipeline.

Usage
    # full run on a config (synthetic example shown):
    python scripts/run_pipeline.py --config config/example_config.yaml

    # validation-only: check config keys, input paths, input columns, module
    # importability and planned output paths WITHOUT reading/processing data:
    python scripts/run_pipeline.py --config config/example_config.yaml --dry-run

    # run a subset of stages:
    python scripts/run_pipeline.py --config config/example_config.yaml --stages 03 04 05

Stages (in order): 01 inventory, 02 validation (optional), 03 exposure,
04 deduplication, 05 indicators, 06 stability_priority.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
sys.path.insert(0, str(SRC))  # so the numbered modules can `import utils`

import utils  # noqa: E402

STAGES = [
    ("01", "01_inventory"),
    ("02", "02_validation"),
    ("03", "03_exposure"),
    ("04", "04_deduplication"),
    ("05", "05_indicators"),
    ("06", "06_stability_priority"),
]

REQUIRED_CONFIG_KEYS = ["crs", "columns", "input", "quality_control",
                        "spatial", "periods", "priority", "hotspot", "paths"]


def load_stage_module(filename: str):
    """Import a numbered stage module (e.g. '03_exposure') by file path."""
    path = SRC / f"{filename}.py"
    if not path.exists():
        raise FileNotFoundError(f"Stage module missing: {path}")
    spec = importlib.util.spec_from_file_location(f"stage_{filename}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def dry_run(cfg: dict) -> int:
    """Validate config, inputs and planned outputs without processing data."""
    utils.log("DRY RUN — validating configuration and inputs (no data processed)")
    ok = True

    missing_keys = [k for k in REQUIRED_CONFIG_KEYS if k not in cfg]
    if missing_keys:
        utils.log(f"  [FAIL] config missing keys: {missing_keys}"); ok = False
    else:
        utils.log("  [ok] all required config sections present")

    # input points existence + columns (header only)
    import pandas as pd
    cols = utils.canonical_columns(cfg)
    src = utils.resolve_path(cfg, cfg["input"]["points_path"])
    if src.is_dir():
        files = sorted(src.glob("*.csv"))
        target = files[0] if files else None
        if not files:
            utils.log(f"  [FAIL] no CSV files in input dir {src}"); ok = False
    else:
        target = src if src.exists() else None
        if target is None:
            utils.log(f"  [WARN] input points_path not found: {src} "
                      f"(expected for restricted real data not in repo)")
    if target is not None:
        head = pd.read_csv(target, nrows=0, encoding="utf-8-sig")
        missing = [c for c in cols.values() if c not in head.columns]
        if missing:
            utils.log(f"  [FAIL] input {target.name} missing columns: {missing}"); ok = False
        else:
            utils.log(f"  [ok] input {target.name} has all required columns")

    # validation path
    vp = cfg["input"].get("validation_path", "")
    if vp:
        vsrc = utils.resolve_path(cfg, vp)
        utils.log(f"  [{'ok' if vsrc.exists() else 'WARN'}] validation_path: {vsrc}")
    else:
        utils.log("  [ok] validation stage will be skipped (no validation_path)")

    # module importability
    for _, fn in STAGES:
        try:
            load_stage_module(fn)
            utils.log(f"  [ok] module {fn} imports")
        except Exception as e:  # pragma: no cover
            utils.log(f"  [FAIL] module {fn}: {type(e).__name__}: {e}"); ok = False

    # planned outputs
    out = utils.resolve_path(cfg, cfg["paths"]["outputs_dir"])
    tab = utils.resolve_path(cfg, cfg["paths"]["tables_dir"])
    utils.log("  planned output locations:")
    for p in [out / "processed" / "all_points_cleaned.csv",
              out / "grid_analysis" / "grid_exposure_full.csv",
              out / "litter_analysis" / "unique_litter_events_full.csv",
              out / "litter_analysis" / "grid_litter_metrics_full.csv",
              out / "stability_priority" / "priority_classification_full_period.csv",
              tab / "validation_summary.csv"]:
        utils.log(f"      {p}")

    utils.log(f"DRY RUN {'PASSED' if ok else 'FAILED'}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True, help="path to a YAML config file")
    ap.add_argument("--dry-run", action="store_true",
                    help="validate config/inputs/outputs only; process no data")
    ap.add_argument("--stages", nargs="*", default=None,
                    help="subset of stage numbers to run, e.g. 03 04 05")
    args = ap.parse_args()

    cfg = utils.load_config(args.config)
    if args.dry_run:
        return dry_run(cfg)

    utils.set_seed(cfg)
    selected = args.stages or [num for num, _ in STAGES]
    for num, fn in STAGES:
        if num not in selected:
            continue
        mod = load_stage_module(fn)
        mod.run(cfg)
    utils.log("PIPELINE COMPLETE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
