# Privacy and data access

## Why the raw data are not public
The raw monitoring materials are governed by municipal operational information and
by the service provider's proprietary materials, and they carry re-identification
and third-party-rights risks. The following are therefore **not** distributed and
will **not** be released:

- raw second-by-second GPS trajectory records;
- raw road images and bounding-box-annotated images;
- precise coordinates that reconstruct collection routes;
- device-to-route correspondences and waste-collection schedule information;
- any license-plate, pedestrian, or residence information that may appear in
  source imagery;
- the upstream Takanome/Pirika detection model, its training data, internal
  thresholds, and internal filtering logic (these are proprietary to the
  operator and were **not available to the authors**).

## What this repository contains
- the complete **downstream post-detection analytical pipeline** (all Python code);
- configuration files and documentation;
- a fully **synthetic** example (`examples/`) with anonymized devices, fictional
  dates and fictional coordinates that are deliberately not in the study region.

## What may become publicly shareable in the future
Subject to written confirmation from Aioi City and Pirika, Inc., a **de-identified,
cell-level analytical dataset** could be archived on Zenodo to support the paper —
for example aggregated 100 m-cell exposure, unique-event counts, normalized
intensity, recurrence ratio, period indicators, priority class, and a
de-identified validation summary. **No commitment of access is made here.** Any
such release must first pass the review in
`../TO_REVIEW_BEFORE_PUBLIC_RELEASE/public_release_review_checklist.md`, because
cell-centre coordinates and dates can still enable route reconstruction.

## Requesting access to restricted materials
Requests for restricted materials may be directed to the corresponding author
of the associated manuscript. Access is **not
guaranteed**: it is contingent on permissions from Aioi City and Pirika, Inc.,
on the intended use, and on appropriate data-handling safeguards. Where access
cannot be granted, the synthetic example and the published code still allow the
analytical workflow to be inspected and re-run on equivalently-structured data.

## Layered release strategy (summary)
**Public:** all Python code; config files; the synthetic example; (future, after
review) a de-identified cell-level analytical dataset and a de-identified
validation summary; aggregate summary tables.
**Not public:** raw second-by-second trajectories; raw images; precise GPS;
device/vehicle business routes; the upstream detection model, training data,
thresholds and internal filtering logic.
