# Road-Litter Priority Pipeline

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21037126.svg)](https://doi.org/10.5281/zenodo.21037126)

A reproducible workflow for exposure-adjusted vehicle-mounted road-litter
monitoring and municipal priority screening.

A configuration-driven Python pipeline that converts vehicle-mounted AI
road-litter detections into exposure-normalized, recurrence-aware municipal
**priority indicators** (HH / HL / LH / LL).

## Associated manuscript

This repository accompanies the downstream analytical workflow described in the
manuscript:

> Cheng, T., Yoshidome, D., Pandyaswargo, A. H., and Onoda, H.
> *From routine municipal collection routes to road-litter management: a
> reproducible framework for exposure-adjusted priority indicators.*

## What this repository is — and is not

> **The upstream detection model, training data, and internal filtering settings
> are proprietary and were not available to the authors. This repository provides
> the complete downstream post-detection processing pipeline developed in this
> study.**

- ✅ Included: the **downstream post-detection analytical pipeline** — quality
  control, trajectory exposure, deduplication, indicators, stability and priority
  classification — plus configuration, documentation, tests and a synthetic example.
- ❌ Not included: the upstream Takanome/Pirika AI detection model, its training
  data and thresholds; and all restricted raw data (trajectories, images, precise
  coordinates, operational/route information). See
  [`docs/privacy_and_data_access.md`](docs/privacy_and_data_access.md).

## Analytical workflow

```
raw point-level records
  → 01 quality control (merge, project, speed flags)
  → 03 trajectory-based observation exposure (100 m grid)
  → effective-coverage screening (n_observation_days ≥ 5)
  → 04 3 m seed-radius deduplication → unique litter events
  → 05 normalized intensity & recurrence ratio
  → 06 period stability (Spearman, Jaccard) + HH/HL/LH/LL priority classes
  → main tables & figures
```

Full diagram and stage descriptions: [`docs/workflow.md`](docs/workflow.md).

## Installation

```bash
git clone https://github.com/CHENG-TIANJIAO/road-litter-priority-pipeline.git
cd road-litter-priority-pipeline
pip install -r requirements.txt          # or: conda env create -f environment.yml
```
Python ≥ 3.9. Core dependencies: numpy, pandas, scipy, pyproj, pyyaml, matplotlib.

## Input data

A point-level CSV (or directory of CSVs) with these columns (names configurable
in `config['columns']`):

| Column | Meaning |
|---|---|
| `pointId` | point identifier |
| `recordDate` | timestamp (local time) |
| `latitude`, `longitude` | WGS84 degrees |
| `device_name` | **anonymized** device id |
| `totalTrashCount` | per-frame detected-object count (≥ 0) |

Rows with `totalTrashCount > 0` are detections; rows with `0` are retained as
trajectory/exposure points. Optional manual-validation labels enable stage 02.
Full schema: [`docs/input_data_schema.md`](docs/input_data_schema.md).

## Run

```bash
# 1) validate config / inputs / outputs only (no data processed):
python scripts/run_pipeline.py --config config/example_config.yaml --dry-run

# 2) run the full pipeline:
python scripts/run_pipeline.py --config config/example_config.yaml

# 3) regenerate the main tables and figures:
python scripts/make_main_tables.py  --config config/example_config.yaml
python scripts/make_main_figures.py --config config/example_config.yaml
```
Use `config/default_config.yaml` as a study-aligned public configuration template
with restricted inputs that are not included in this repository, or use
`config/example_config.yaml` with the bundled synthetic data.

## Outputs

| Location | Contents |
|---|---|
| `outputs/processed/` | cleaned point table with speed flags |
| `outputs/grid_analysis/` | per-cell exposure (full / period1 / period2) |
| `outputs/litter_analysis/` | unique litter events; per-cell intensity & recurrence |
| `outputs/stability_priority/` | priority classes, hotspot overlap, stability summary |
| `tables/`, `figures/` | main tables and figures |

Field-by-field definitions: [`docs/output_data_schema.md`](docs/output_data_schema.md).

## Parameters

All in one YAML file (`config/*.yaml`):

| Parameter | Default | Meaning |
|---|---|---|
| `crs.projected` | `EPSG:6673` | metric CRS for distances/gridding |
| `quality_control.speed_abnormal_kmh / gps_jump_dist_m / gps_jump_dt_sec` | 120 / 1000 / 60 | speed-flag thresholds |
| `spatial.grid_size_m` | 100 | grid cell size |
| `spatial.dedup_radius_m` | 3.0 | seed-radius deduplication |
| `spatial.effective_observation_days_min` | 5 | effective-coverage threshold |
| `periods.*` | study dates | full / period1 / period2 |
| `priority.main_percentile` | 80 | HH/HL/LH/LL split |
| `hotspot.top_x_percent` | [5,10,20] | hotspot-overlap definitions |

## Synthetic example

A fully **synthetic** dataset (anonymized devices `DEV_A/B/C`, fictional dates and
coordinates that are *not* in the study region) exercises the entire workflow:

```bash
python examples/generate_synthetic_input.py
python scripts/run_pipeline.py --config config/example_config.yaml
python -m pytest tests/ -q
```
Expected results are committed under `examples/expected_output/`.

## Reproducibility

The pipeline is deterministic; the synthetic generator and any stochastic
extension use a fixed seed. See [`docs/reproducibility.md`](docs/reproducibility.md)
for the environment, run order and the manuscript ↔ code-version mapping.

> The spatial analytical pipeline was independently re-executed against the
> restricted study data and reproduced the manuscript outputs at cell level. The
> public validation module is designed for de-identified validation-label inputs;
> the original annotation workbooks remain restricted and are not distributed with
> this repository.

## Data and confidentiality

This repository contains the downstream analytical code, synthetic example data,
documentation, and tests only.

The restricted study data are not included, including raw second-by-second
trajectories, road images, annotated bounding-box images, precise georeferenced
detections, original manual-validation workbooks, municipal operational route
information, and the proprietary upstream AI detection model.

The pipeline was independently executed on the restricted study data and
reproduced the reported spatial outputs at the individual grid-cell level.

A de-identified, cell-level analytical dataset may be shared in future subject to
written permission from Aioi City and Pirika, Inc. See
[`docs/privacy_and_data_access.md`](docs/privacy_and_data_access.md).

## Citation

Please cite this software using the metadata in [`CITATION.cff`](CITATION.cff).
The associated manuscript is listed above under **Associated manuscript**.

Archived on Zenodo. Cite this version: https://doi.org/10.5281/zenodo.21037127
(all versions: https://doi.org/10.5281/zenodo.21037126).

## License

- **Code:** MIT — see [`LICENSE`](LICENSE).
- **Documentation and de-identified derived data:** CC-BY-4.0 — see
  [`docs/DATA_AND_DOCUMENTATION_LICENSE.md`](docs/DATA_AND_DOCUMENTATION_LICENSE.md).
- **Raw data:** not distributed and **not** offered under any open license.
