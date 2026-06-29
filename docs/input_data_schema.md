# Input data schema

The pipeline reads only the columns below. Column **names are configurable** in
`config['columns']`; the defaults match the public schema used by the synthetic
example. Any additional columns present in a source file (for example image URLs
or capture identifiers in the restricted raw data) are **ignored and never
required** — they are not read into the pipeline.

> The real point-level input is **not distributed** with this repository (see
> `docs/privacy_and_data_access.md`). The schema below documents the structure so
> that a holder of equivalently-structured data can run the pipeline.

## 1. Point-level detection records (required)

`config['input']['points_path']` — a single CSV or a directory of CSVs.

| Logical name | Default column | Type | Unit | Required | Example (synthetic) |
|---|---|---|---|---|---|
| point id | `pointId` | string | — | yes | `P000123` |
| timestamp | `recordDate` | datetime-parseable string | local time | yes | `2001-01-03 09:00:05` |
| latitude | `latitude` | float | degrees (WGS84) | yes | `40.001100` |
| longitude | `longitude` | float | degrees (WGS84) | yes | `140.001650` |
| device id | `device_name` | string (anonymized) | — | yes | `DEV_A` |
| detected count | `totalTrashCount` | integer ≥ 0 | objects/frame | yes | `2` |

Notes
- A row is a **detection** when `totalTrashCount > 0`; rows with `0` are retained
  as trajectory (exposure) points and are essential for the exposure denominator.
- `device_name` must be an **anonymized** identifier (e.g. `DEV_A`); do not use
  values that map to real vehicles, operators or routes.
- Rows missing coordinates or an unparseable timestamp are dropped (and counted)
  at stage 01; rows outside the configured QC bounding box are **logged, not
  dropped**.

## 2. Manual-validation labels (optional)

`config['input']['validation_path']` — leave empty to skip stage 02.

| Logical name | Default column | Type | Required | Example |
|---|---|---|---|---|
| point id | `pointId` | string | yes | `P000123` |
| timestamp | `recordDate` | datetime string | yes | `2001-01-03 09:00:05` |
| device id | `device_name` | string | yes | `DEV_A` |
| manual label | `manual_label` | string | yes | `true_litter` / `false_positive` |
| FP cause | `false_positive_type` | string | no | `road_marking` |
| detected count | `totalTrashCount` | integer | no (enables object-level rates) | `2` |

`manual_label == "true_litter"` is treated as a valid detection; any other value
is treated as a false positive.

## Validation behaviour

`scripts/run_pipeline.py --dry-run` checks that every required column is present
and reports missing columns with a human-readable error before any data is
processed. See `docs/output_data_schema.md` for the produced fields.
