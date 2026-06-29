"""
generate_synthetic_input.py — create the bundled SYNTHETIC example input.

This generates examples/synthetic_input/synthetic_points.csv and
synthetic_validation.csv. Everything is fabricated from a fixed seed:

  * anonymized devices: DEV_A, DEV_B, DEV_C
  * FICTIONAL coordinates near lat 40.0, lon 140.0 — deliberately NOT in
    Aioi City, Hyogo Prefecture, or the real study region
  * FICTIONAL dates in the year 2001
  * detection patterns designed so the downstream pipeline produces a spread
    of HH / HL / LH / LL priority cells and some 3 m deduplication clusters

No real Aioi/Pirika data is read or perturbed. Run:

    python examples/generate_synthetic_input.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

OUT_DIR = Path(__file__).resolve().parent / "synthetic_input"
SEED = 12345

# Fictional anchor (NOT the study area). ~0.0011 deg ~ 100 m here.
LAT0, LON0 = 40.0000, 140.0000
DEG = 0.0011                       # approx one 100 m cell step in degrees
DEVICES = ["DEV_A", "DEV_B", "DEV_C"]

# Visit days (distinct calendar days) per period -> >=5 gives effective coverage.
P1_DAYS = [f"2001-01-{d:02d}" for d in (3, 6, 9, 12, 15, 18, 21, 24)]
P2_DAYS = [f"2001-02-{d:02d}" for d in (2, 5, 8, 11, 14, 17, 20, 23)]

# 16 route-cells, each given a (n_events, detection_days) profile so that the
# 80th-percentile split yields all four quadrants, plus 2 under-sampled cells.
#   n_events high (3) -> high intensity ; detection_days high (8) -> high recurrence
PROFILES = []
for i in range(4):
    PROFILES.append(dict(n_events=3, det_days=8))   # -> HH
for i in range(4):
    PROFILES.append(dict(n_events=3, det_days=2))   # -> HL
for i in range(4):
    PROFILES.append(dict(n_events=1, det_days=8))   # -> LH
for i in range(4):
    PROFILES.append(dict(n_events=1, det_days=1))   # -> LL


def main() -> int:
    rng = np.random.default_rng(SEED)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    point_rows = []
    val_rows = []
    pid = 0
    clock = {}   # (device, day) -> next second offset; gives monotonic 1 s steps

    def emit(device, day, lat, lon, ttc):
        nonlocal pid
        pid += 1
        sec = clock.get((device, day), 0)
        clock[(device, day)] = sec + 1
        ts = (pd.Timestamp(day) + pd.Timedelta(hours=9, seconds=sec)).strftime("%Y-%m-%d %H:%M:%S")
        point_rows.append(dict(pointId=f"P{pid:06d}", recordDate=ts,
                               latitude=round(lat, 7), longitude=round(lon, 7),
                               device_name=device, totalTrashCount=int(ttc)))
        return f"P{pid:06d}", ts

    # cell grid layout: 4 columns x 4 rows of route-cells + 2 extra under-sampled
    for ci, prof in enumerate(PROFILES):
        col, row = ci % 4, ci // 4
        base_lat = LAT0 + row * DEG * 1.5
        base_lon = LON0 + col * DEG * 1.5
        # fixed event locations inside this cell, >4 m apart
        event_offsets = [(0.00002, 0.00002), (0.00045, 0.00010), (0.00010, 0.00045)]
        events = event_offsets[: prof["n_events"]]

        for period_days in (P1_DAYS, P2_DAYS):
            det_days = set(period_days[: prof["det_days"]])
            for device in DEVICES:
                for day in period_days:
                    # ~7 trajectory points crossing the cell (~10 m apart)
                    for k in range(7):
                        lat = base_lat + k * 0.00009 + rng.normal(0, 1e-6)
                        lon = base_lon + k * 0.00002 + rng.normal(0, 1e-6)
                        emit(device, day, lat, lon, 0)
                    # detections on detection-days: one row per event location
                    if day in det_days:
                        for (dlat, dlon) in events:
                            jlat = base_lat + dlat + rng.normal(0, 5e-6)   # <3 m jitter
                            jlon = base_lon + dlon + rng.normal(0, 5e-6)
                            ttc = int(rng.integers(1, 4))
                            ppid, ts = emit(device, day, jlat, jlon, ttc)
                            # validation labels: ~92% true, rest FP with a cause
                            if rng.random() < 0.08:
                                cause = rng.choice(["road_marking", "shadow", "natural_object"])
                                val_rows.append(dict(pointId=ppid, recordDate=ts,
                                                     device_name=device,
                                                     manual_label="false_positive",
                                                     false_positive_type=cause,
                                                     totalTrashCount=ttc))
                            else:
                                val_rows.append(dict(pointId=ppid, recordDate=ts,
                                                     device_name=device,
                                                     manual_label="true_litter",
                                                     false_positive_type="",
                                                     totalTrashCount=ttc))

    # 2 deliberately under-sampled cells (visited on <5 days -> non-effective)
    for j in range(2):
        base_lat = LAT0 - DEG * (j + 1) * 1.5
        base_lon = LON0 - DEG * 1.5
        for day in P1_DAYS[:3]:
            for k in range(7):
                emit("DEV_A", day, base_lat + k * 0.00009, base_lon + k * 0.00002, 0)
            ppid, ts = emit("DEV_A", day, base_lat + 0.0001, base_lon + 0.0001, 1)
            val_rows.append(dict(pointId=ppid, recordDate=ts, device_name="DEV_A",
                                 manual_label="true_litter", false_positive_type="",
                                 totalTrashCount=1))

    pts = pd.DataFrame(point_rows)
    val = pd.DataFrame(val_rows)
    pts.to_csv(OUT_DIR / "synthetic_points.csv", index=False, encoding="utf-8")
    val.to_csv(OUT_DIR / "synthetic_validation.csv", index=False, encoding="utf-8")
    print(f"wrote {len(pts):,} synthetic point rows -> synthetic_points.csv")
    print(f"wrote {len(val):,} synthetic validation rows -> synthetic_validation.csv")
    print(f"detections (ttc>0): {int((pts['totalTrashCount'] > 0).sum()):,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
