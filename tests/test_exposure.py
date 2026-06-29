"""Unit tests for stage 03 exposure: observation counts, valid driving distance
(only 'ok' segments contribute) and effective-coverage flag."""
from __future__ import annotations

import numpy as np
import pandas as pd
from conftest import load_module, IdentityTransformer

exposure = load_module("03_exposure")


def _prepped_rows():
    """One effective cell (0,0) visited on 5 days; one non-effective cell (1,0)
    visited on 2 days. Some segments are excluded (seg_excluded=1, contribute 0 m)."""
    rows = []
    # cell (0,0): 5 distinct days, device DEV_A; each day one ok 10 m segment
    for d in range(1, 6):
        rows.append(dict(cell_ix=0, cell_iy=0, pointId=f"a{d}",
                         date_only=pd.Timestamp(f"2001-01-0{d}"),
                         device_short="DEV_A", seg_excluded=0, valid_dist_m=10.0,
                         is_detection=False, ttc_for_sum=0.0))
    # cell (0,0): one excluded segment (abnormal) -> 0 valid distance, but counts as a point/day already covered
    rows.append(dict(cell_ix=0, cell_iy=0, pointId="a_excl",
                     date_only=pd.Timestamp("2001-01-05"),
                     device_short="DEV_A", seg_excluded=1, valid_dist_m=0.0,
                     is_detection=True, ttc_for_sum=2.0))
    # cell (1,0): 2 distinct days only -> non-effective
    for d in range(1, 3):
        rows.append(dict(cell_ix=1, cell_iy=0, pointId=f"b{d}",
                         date_only=pd.Timestamp(f"2001-01-0{d}"),
                         device_short="DEV_B", seg_excluded=0, valid_dist_m=20.0,
                         is_detection=False, ttc_for_sum=0.0))
    return pd.DataFrame(rows)


def test_exposure_counts_and_valid_distance():
    g = exposure.aggregate_exposure(_prepped_rows(), grid_size_m=100, eff_days_min=5,
                                    inv_transformer=IdentityTransformer(),
                                    period_label="full", period_start="2001-01-01",
                                    period_end="2001-03-01")
    c00 = g[g["grid_id"] == "0_0"].iloc[0]
    c10 = g[g["grid_id"] == "1_0"].iloc[0]

    # cell (0,0): 6 points, 5 distinct days, valid distance = 5 * 10 m (excluded adds 0)
    assert c00["n_observation_points"] == 6
    assert c00["n_observation_days"] == 5
    assert c00["valid_distance_m"] == 50.0
    assert c00["n_points_excluded_abnormal_segments"] == 1
    assert bool(c00["is_effective_coverage"]) is True

    # cell (1,0): 2 days -> not effective; valid distance = 2 * 20 m
    assert c10["n_observation_days"] == 2
    assert bool(c10["is_effective_coverage"]) is False
    assert c10["valid_distance_m"] == 40.0


def test_valid_distance_km_conversion():
    g = exposure.aggregate_exposure(_prepped_rows(), grid_size_m=100, eff_days_min=5,
                                    inv_transformer=IdentityTransformer(),
                                    period_label="full", period_start="2001-01-01",
                                    period_end="2001-03-01")
    c00 = g[g["grid_id"] == "0_0"].iloc[0]
    assert np.isclose(c00["valid_distance_km"], c00["valid_distance_m"] / 1000.0)
