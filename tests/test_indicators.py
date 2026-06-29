"""Unit tests for stage 05 indicators: normalized intensity, recurrence ratio,
and non-effective / zero-exposure handling."""
from __future__ import annotations

import numpy as np
import pandas as pd
from conftest import load_module

ind = load_module("05_indicators")


def test_normalized_intensity_formula():
    out = ind.normalized_intensity(n_events=[4, 0, 3], valid_distance_km=[2.0, 1.0, 0.0])
    assert out[0] == 2.0          # 4 events / 2 km
    assert out[1] == 0.0          # 0 events / 1 km
    assert np.isnan(out[2])       # zero valid distance -> NaN


def test_recurrence_ratio_formula_and_bounds():
    out = ind.recurrence_ratio(n_detection_days=[3, 0, 5], n_observation_days=[6, 4, 5])
    assert np.isclose(out[0], 0.5)
    assert out[1] == 0.0
    assert np.isclose(out[2], 1.0)            # bounded at 1
    assert np.all((out[np.isfinite(out)] >= 0) & (out[np.isfinite(out)] <= 1))


def test_recurrence_zero_observation_days_is_nan():
    out = ind.recurrence_ratio(n_detection_days=[1], n_observation_days=[0])
    assert np.isnan(out[0])


def test_build_metrics_non_effective_handling():
    # one effective cell with valid distance, one non-effective (3 obs days)
    exposure = pd.DataFrame([
        dict(grid_id="0_0", cell_ix=0, cell_iy=0, lon_center=0.0, lat_center=0.0,
             n_observation_points=10, n_observation_days=6, n_devices_observed=1,
             valid_distance_m=2000.0, valid_distance_km=2.0, is_effective_coverage=True,
             period_label="full", period_start="s", period_end="e"),
        dict(grid_id="1_0", cell_ix=1, cell_iy=0, lon_center=0.0, lat_center=0.0,
             n_observation_points=4, n_observation_days=3, n_devices_observed=1,
             valid_distance_m=500.0, valid_distance_km=0.5, is_effective_coverage=False,
             period_label="full", period_start="s", period_end="e"),
    ])
    events = pd.DataFrame([dict(grid_id="0_0"), dict(grid_id="0_0"),
                           dict(grid_id="0_0"), dict(grid_id="0_0"),
                           dict(grid_id="1_0")])  # 4 events in 0_0, 1 in 1_0
    det_days = pd.DataFrame([dict(grid_id="0_0", n_detection_days=3),
                             dict(grid_id="1_0", n_detection_days=1)])
    m = ind.build_metrics(exposure, events, det_days, eff_days_min=5)

    eff = m[m["grid_id"] == "0_0"].iloc[0]
    non = m[m["grid_id"] == "1_0"].iloc[0]

    assert eff["metric_status"] == "effective"
    assert np.isclose(eff["normalized_intensity_per_km"], 4 / 2.0)   # 2.0
    assert np.isclose(eff["recurrence_ratio"], 3 / 6)                # 0.5

    # non-effective cell: formal normalized intensity blanked to NaN
    assert non["metric_status"] == "not_effective"
    assert np.isnan(non["normalized_intensity_per_km"])
