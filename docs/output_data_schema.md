# Output data schema

All outputs are written under `config['paths']['outputs_dir']` (and tables under
`tables_dir`). For the synthetic example these resolve to
`examples/expected_output/`.

## Stage 01 — `processed/all_points_cleaned.csv`
Point-level cleaned table (one row per input point).

| Field | Meaning |
|---|---|
| `pointId, recordDate, latitude, longitude, device_name, totalTrashCount` | carried from input |
| `date_ts` | parsed timestamp |
| `is_detection` | `totalTrashCount > 0` |
| `x_m, y_m` | projected coordinates (metric CRS) |
| `dist_m, dt_sec, speed_kmh` | inter-point distance, time gap, instantaneous speed (per device, time-ordered) |
| `speed_flag` | one of `first_row, dt_nonpositive, gps_jump, abnormal_high, ok` |
| `device_short, source_file` | helper / provenance |

## Stage 03 — `grid_analysis/grid_exposure_{full,period1,period2}.csv`
One row per 100 m cell per period.

| Field | Meaning |
|---|---|
| `grid_id, cell_ix, cell_iy` | cell identity (floor of projected coords / grid size) |
| `x_center_m, y_center_m, lon_center, lat_center` | cell-centre coordinates |
| `n_observation_points` | trajectory rows in the cell |
| `n_observation_days` | distinct calendar dates observed |
| `n_devices_observed` | distinct devices |
| `n_points_excluded_abnormal_segments` | rows whose incoming segment was not `ok` |
| `valid_distance_m, valid_distance_km` | summed distance over `ok` segments |
| `n_detection_rows_raw, sum_totalTrashCount_raw` | raw detection references (pre-dedup) |
| `is_effective_coverage` | `n_observation_days >= effective_observation_days_min` |
| `period_label, period_start, period_end` | period metadata |

## Stage 04 — `litter_analysis/unique_litter_events_{...}.csv`
One row per unique litter event (3 m seed-radius cluster).

| Field | Meaning |
|---|---|
| `cluster_id` | event id within the period |
| `n_member_rows` | detection rows collapsed into the event |
| `centroid_x_m, centroid_y_m` | event centroid (projected) |
| `max_distance_from_seed_m` | bounded by `dedup_radius_m` by construction |
| `cell_ix, cell_iy, grid_id` | 100 m cell of the centroid |
| `period_label` | period metadata |

## Stage 05 — `litter_analysis/grid_litter_metrics_{...}.csv`
Per-cell indicators.

| Field | Meaning |
|---|---|
| `n_unique_litter_events` | events attributed to the cell |
| `n_detection_days` | distinct dates with any raw detection in the cell |
| `normalized_intensity_per_km` | `n_unique_litter_events / valid_distance_km` (NaN unless `effective` and `valid_km>0`) |
| `recurrence_ratio` | `n_detection_days / n_observation_days` ∈ [0, 1] |
| `metric_status` | `effective` / `not_effective` / `div_zero` |
| (+ exposure fields carried from stage 03) | |

## Stage 06 — `stability_priority/`

`priority_classification_full_period.csv` — per-cell `priority_class` ∈
{`HH, HL, LH, LL, non_effective`} plus the `intensity_threshold_p80` /
`recurrence_threshold_p80` used.

`period_hotspot_overlap.csv` — for each top-X%: `threshold_p1/p2`, intersection
counts and `jaccard`.

`persistent_emerging_declining_hotspots.csv` — `grid_id, category`.

`stability_summary.txt` — Spearman ρ (with Fisher-z CI) for intensity and
recurrence, Jaccard overlaps, class counts and percentile-sensitivity rows.

## Tables (`tables_dir`)
`validation_summary.csv` (stage 02); `table1_study_data_exposure.csv`,
`table2_validation.csv`, `table3_stability_priority.csv`
(via `scripts/make_main_tables.py`).
