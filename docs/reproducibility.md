# Reproducibility

## Software environment
- Python ≥ 3.9
- Core: `numpy`, `pandas`, `scipy`, `pyproj`, `pyyaml`, `matplotlib`
- Optional: `geopandas` (only if you extend the code to write GeoPackages),
  `pytest` (tests)
- Install with `pip install -r requirements.txt` or
  `conda env create -f environment.yml`.

## Run order
The stages are strictly ordered and `run_pipeline.py` enforces it:
`01 inventory → 02 validation (optional) → 03 exposure → 04 deduplication →
05 indicators → 06 stability/priority`, then optionally
`make_main_tables.py` and `make_main_figures.py`.

## Determinism and seeds
- The analytical pipeline is **deterministic**: given the same input and config
  it produces byte-stable CSV outputs (no randomness in stages 01–06).
- A global seed is set from `config['random_seed']` in `utils.set_seed()` as a
  safeguard for any future stochastic extension.
- The **synthetic example generator** (`examples/generate_synthetic_input.py`)
  uses a fixed seed (`SEED = 12345`), so it regenerates identical synthetic input.

## Check your installation with the synthetic example
```bash
python examples/generate_synthetic_input.py
python scripts/run_pipeline.py --config config/example_config.yaml --dry-run
python scripts/run_pipeline.py --config config/example_config.yaml
python scripts/make_main_tables.py  --config config/example_config.yaml
python scripts/make_main_figures.py --config config/example_config.yaml
python -m pytest tests/ -q
```
Expected: the dry-run reports `DRY RUN PASSED`; the full run logs all six stages;
`examples/expected_output/` is reproduced (≈33 cells, all four priority classes
present in the synthetic case); all unit tests pass.

## Manuscript ↔ code version correspondence
| Item | Value |
|---|---|
| Manuscript | "From routine municipal collection routes to road-litter management: a reproducible framework for exposure-adjusted priority indicators" |
| Code version | see `CHANGELOG.md` / the git tag used for the Zenodo release (e.g. `v1.0.0`) |
| Zenodo DOI | added after the first GitHub release is archived |

The manuscript numbers were produced from the **restricted real inputs** with the
parameters in `config/default_config.yaml`. Those inputs are not in this
repository; the synthetic example demonstrates the identical code path on
fabricated data. Any change that could affect the manuscript numbers is recorded
in `CHANGELOG.md` under an explicit "calculation caliber" note.

## Restricted-data reproducibility audit (method)
Before tagging the paper-submission version, a **local, offline** audit was run
on the restricted real data (which are not distributed here).

- **Spatial analytical pipeline (stages 01, 03–06).** This refactored pipeline was
  independently re-executed on the same restricted study data and compared,
  metric-by-metric, against (i) the original analysis project's outputs and (ii)
  the values reported in the manuscript. The comparison covered the dataset scale,
  speed-flag distribution, per-period valid driving distance, effective-cell
  counts, unique-event counts, the joined effective set, Spearman correlations,
  top-X% Jaccard overlap, persistent/emerging/declining counts, the 80th-percentile
  priority thresholds, and the HH/HL/LH/LL/non-effective class counts. Acceptance
  required exact agreement on all discrete values and agreement within `1e-8` on
  floating-point values, plus a **per-cell identity check**. **Result:** every
  metric reproduced and **all grid cells were identical**, confirming the refactor
  changed no calculation caliber or spatial manuscript result.
- **Validation module (stage 02).** The public validation module is designed for a
  **de-identified validation-label input schema** and was **not** re-executed on
  the restricted data. The original manual-annotation workbooks remain restricted
  and are **not** distributed with this repository. The manuscript's validation
  summary (false-positive rates, validated record/object counts) was cross-checked
  against the original project's authoritative validation outputs and is consistent;
  it was not recomputed by the public module.

The audit script, its configuration and all real-data outputs are kept strictly
local and excluded from version control (`local_audit_not_for_release/`,
`config/local_restricted_config.yaml`); no real coordinates, routes, images or
per-cell data are included in this repository.
