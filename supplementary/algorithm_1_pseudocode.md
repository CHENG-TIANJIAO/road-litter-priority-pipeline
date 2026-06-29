# Algorithm 1. Reproducible post-detection pipeline for municipal road-litter priority indicators

**Inputs.** Point-level records `R = {(pointId, recordDate, lat, lon, device,
totalTrashCount)}`; parameters: projected CRS, grid size `g` (100 m),
deduplication radius `r` (3 m), effective-coverage threshold `D_min` (5 days),
period split (P1, P2), priority percentile `q` (80), speed thresholds
(`v_max`=120 km/h, jump `d>1000 m` within `Δt<60 s`).

**Output.** Per-cell indicators and a HH/HL/LH/LL/non-effective priority class;
period-stability statistics.

```
# --- Stage 01: merge & quality control -------------------------------------
1  R <- merge and standardize all input record files
2  parse recordDate -> timestamp; drop rows with missing coordinate/time (count them)
3  project (lon, lat) -> (x_m, y_m) in the projected CRS
4  for each device, in time order:
5      Δd <- Euclidean distance to previous point;  Δt <- time gap
6      v  <- (Δd / Δt) * 3.6                                   # km/h
7      assign ONE speed flag (priority: first_row > dt_nonpositive
8          > gps_jump (Δd>1000 m and Δt<60 s) > abnormal_high (v>v_max) > ok)
9  is_detection <- (totalTrashCount > 0)        # no row is ever deleted

# --- Stage 03: observation exposure on a 100 m grid ------------------------
10 cell_ix <- floor(x_m / g);  cell_iy <- floor(y_m / g)       # origin (0,0)
11 for each period in {full, P1, P2}, group rows by cell:
12     n_observation_points <- count of rows
13     n_observation_days   <- distinct calendar dates
14     n_devices_observed   <- distinct devices
15     valid_distance_m     <- sum of Δd over 'ok' segments only
16     is_effective         <- (n_observation_days >= D_min)

# --- Stage 04: 3 m seed-radius deduplication -------------------------------
17 for each period, take detection rows; sort by (recordDate, pointId)
18 cluster <- {}                                              # seed-radius clustering
19 for k = 1..n in seed order:
20     if row k already assigned: continue
21     seed <- row k; open a new cluster
22     assign every still-unassigned row within r of the seed to this cluster
23         # members do NOT seed further growth -> no single-link chaining
24 each cluster = one unique litter event; centroid <- mean(member x_m, y_m)
25 attribute each event to the 100 m cell containing its centroid

# --- Stage 05: indicators --------------------------------------------------
26 n_unique_litter_events[cell] <- number of event centroids in the cell
27 n_detection_days[cell]       <- distinct dates with any RAW detection in the cell
28 normalized_intensity_per_km  <- n_unique_litter_events / valid_distance_km
29 recurrence_ratio             <- n_detection_days / n_observation_days   # in [0,1]
30 mark formal values only for effective cells with valid_distance_km > 0

# --- Stage 06a: period stability (P1 vs P2) --------------------------------
31 join cells effective in BOTH periods
32 Spearman rho for normalized_intensity and for recurrence (Fisher-z CIs)
33 for X in {5,10,20}: top-X% = cells above each period's own (100-X) percentile
34     Jaccard overlap on the joined inner-effective set
35 persistent = top10 in both; emerging = outside top20 P1 & top10 P2;
36 declining  = top10 P1 & outside top20 P2

# --- Stage 06b: management-priority classification -------------------------
37 among FULL-period effective cells with >= 1 unique event:
38     t_int <- q-th percentile of normalized_intensity
39     t_rec <- q-th percentile of recurrence_ratio
40 for each full-period effective cell:
41     HH if intensity>=t_int and recurrence>=t_rec
42     HL if intensity>=t_int and recurrence< t_rec
43     LH if intensity< t_int and recurrence>=t_rec
44     LL otherwise
45 cells without effective coverage -> non_effective

# --- Export ----------------------------------------------------------------
46 write cell tables, stability statistics, main tables and figures
```

**Notes.** The seed-radius rule (lines 19–23) is what bounds every cluster within
`r` of its seed and prevents the chain-like over-merging of single-link
agglomerative clustering. `n_detection_days` (line 27) is computed from raw
detection rows, not from clusters, so recurrence retains a temporal interpretation
independent of how many distinct items contributed. Thresholds (lines 38–39) are
derived from the data, not hard-coded.
