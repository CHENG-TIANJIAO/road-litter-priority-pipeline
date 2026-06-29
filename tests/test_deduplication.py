"""Unit tests for stage 04 deduplication: the 3 m seed-radius rule must NOT
produce single-link chain over-merging, and near-duplicate detections collapse
to one unique event."""
from __future__ import annotations

import numpy as np
import pandas as pd
from conftest import load_module

dedup = load_module("04_deduplication")


def test_no_single_link_chaining():
    """A--B--C with d(A,B)=2 m, d(B,C)=2 m, d(A,C)=4 m. Single-link clustering
    would merge all three; seed-radius (3 m) must NOT: A seeds, B joins A;
    C is >3 m from seed A so it starts its own cluster."""
    xy = np.array([[0.0, 0.0],   # A (seed)
                   [2.0, 0.0],   # B (within 3 m of A)
                   [4.0, 0.0]])  # C (4 m from A -> not merged via B)
    clusters = dedup.seed_radius_clusters(xy, radius_m=3.0)
    assert clusters[0] == clusters[1]          # A and B together
    assert clusters[2] != clusters[0]          # C separate (no chaining)
    assert len(set(clusters)) == 2


def test_member_within_radius_of_seed():
    rng = np.random.default_rng(0)
    # 20 points within 1 m of origin + 1 far point
    near = rng.normal(0, 0.3, size=(20, 2))
    far = np.array([[100.0, 100.0]])
    xy = np.vstack([near, far])
    clusters = dedup.seed_radius_clusters(xy, radius_m=3.0)
    # the 20 near points share one cluster; far point is its own
    assert len(set(clusters[:20])) == 1
    assert clusters[20] != clusters[0]


def test_repeated_detections_collapse_to_one_event():
    """Same litter item detected on 5 days (<3 m jitter) -> 1 unique event."""
    rows = []
    for d in range(1, 6):
        rows.append(dict(pointId=f"p{d}", recordDate=f"2001-01-0{d} 09:00:00",
                         x_m=1000.0 + 0.5 * d, y_m=2000.0 + 0.5 * d))  # within ~3 m
    det = pd.DataFrame(rows)
    tbl = dedup.cluster_table(det, radius_m=3.0, grid_size_m=100)
    assert len(tbl) == 1
    assert int(tbl["n_member_rows"].iloc[0]) == 5
    assert tbl["max_distance_from_seed_m"].iloc[0] <= 3.0 + 1e-9
