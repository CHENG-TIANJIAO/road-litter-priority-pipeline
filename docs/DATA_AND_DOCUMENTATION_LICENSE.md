# License for documentation and de-identified derived data

## Summary of licensing in this repository
This repository uses **two different licenses**, and a clear **exclusion**:

| Material | License |
|---|---|
| Source code (everything under `src/`, `scripts/`, `tests/`, `examples/*.py`) | **MIT** — see `../LICENSE` |
| Documentation (`docs/`, `README.md`, `supplementary/`) and any **de-identified, derived** data files that may be released in future (e.g. cell-level analytical outputs, synthetic example data) | **CC-BY-4.0** — this document |
| Raw monitoring data (trajectories, images, precise coordinates, operational/route information, the upstream detection model and its internals) | **NOT licensed for reuse here — not distributed at all** |

## Documentation & derived-data license (CC-BY-4.0)
The documentation in this repository, and any de-identified derived data that the
authors may publish under this repository in the future, are licensed under the
**Creative Commons Attribution 4.0 International (CC-BY-4.0)** license:
https://creativecommons.org/licenses/by/4.0/

You are free to share and adapt this material for any purpose, provided you give
appropriate credit (cite the paper and this repository / its Zenodo DOI).

## Important exclusion — raw data are NOT CC-BY
The CC-BY-4.0 license above applies **only** to documentation and to de-identified
derived data that are explicitly published in this repository. It does **not**
apply to, and confers **no rights over**:

- raw second-by-second GPS trajectories, road images or bounding-box images;
- precise georeferenced detections or route-reconstructing coordinates;
- municipal operational/collection-schedule information;
- the upstream Takanome/Pirika AI detection model, its training data, thresholds
  or internal filtering logic.

These materials are restricted, are **not distributed** with this repository, and
are **not** offered under CC-BY-4.0 or any other open license (see
`privacy_and_data_access.md`). Nothing in this repository should be read as
granting permission to obtain, reuse, or redistribute those restricted materials.

## Code license
The source code is licensed separately under the MIT License; see the `LICENSE`
file at the repository root.
