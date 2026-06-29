# Changelog

All notable changes to this repository are documented here. Versions follow
[Semantic Versioning](https://semver.org/). Each release also records whether the
**calculation caliber** differs from the manuscript analysis version.

## [v1.0.0-paper-submission] — 2026-06-29
Frozen computational record corresponding to the manuscript submission.

- The **core spatial pipeline** (stages 01, 03–06: quality control, observation
  exposure, 3 m seed-radius deduplication, intensity/recurrence indicators,
  period stability and HH/HL/LH/LL priority classification) was **verified against
  the restricted study data** in a local, offline audit.
- **All manuscript-level spatial outputs were reproduced exactly**, including a
  per-cell identity check in which every grid cell received the same priority
  class and identical indicators (discrete values exact; floats within `1e-8`).
  No calculation caliber changed in the refactor.
- **Restricted-data boundary for validation:** the public validation module
  (stage 02) accepts a de-identified validation-label schema; the original manual
  annotation workbooks are **restricted and not distributed**, and were not used
  as input to the public module. The manuscript validation summary was
  cross-checked against the original project's authoritative outputs and is
  consistent.
- This record adds no real numerical results beyond those already reported in the
  manuscript. The audit script, its config and all real-data outputs are kept
  local and excluded from version control.

## [1.0.0] — 2026-06-29
First public-preparation release of the downstream post-detection analytical
pipeline.

### Added
- `src/` config-driven stages: `01_inventory`, `02_validation`, `03_exposure`,
  `04_deduplication`, `05_indicators`, `06_stability_priority`, `utils`.
- `scripts/run_pipeline.py` (with `--config`, `--dry-run`, `--stages`),
  `make_main_tables.py`, `make_main_figures.py`.
- `config/default_config.yaml` (real study parameters) and
  `config/example_config.yaml` (synthetic example).
- Fully synthetic example (`examples/`) + committed `expected_output/`.
- Unit tests (`tests/`) for exposure, seed-radius deduplication, and indicators.
- Documentation (`docs/`), supplementary pseudocode and architecture table,
  licensing files, and the public-release review folder.

### Calculation-caliber note vs. the manuscript analysis version
- This repository is a **refactor** of the original analysis scripts into a
  configuration-driven form. The **core computational caliber is unchanged**:
  same metric CRS (EPSG:6673), 100 m grid floored at the projected origin,
  speed-flag thresholds (120 km/h; jump > 1000 m within < 60 s), effective
  coverage `n_observation_days ≥ 5`, 3 m seed-radius deduplication
  (scipy `cKDTree`, no single-link chaining), `normalized_intensity_per_km =
  unique_events / valid_km`, `recurrence_ratio = detection_days / observation_days`,
  and 80th-percentile HH/HL/LH/LL thresholds derived from the data.
- **Known presentation-level differences (do not change the numbers):**
  output **file names** were standardized (e.g. `grid_exposure_period1.csv`
  instead of the dated `..._period1_20251218_20260115.csv`); GeoPackage writing
  is not ported (CSV outputs only); `make_main_figures.py` produces clean,
  reproducible renderings rather than the publication-polished figures.
- No change to any reported result number is introduced by this refactor. Should
  any future change affect the manuscript numbers, it will be recorded here
  explicitly.

## [Unreleased]
- Zenodo DOI to be inserted into `README.md`, `CITATION.cff`, and the manuscript
  statements after archival (see `docs/zenodo_release_checklist.md`).
