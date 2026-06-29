# Manuscript insert drafts (English)

Cautious, academic wording for direct use in the manuscript and cover letter.
These statements do **not** claim that the raw data are public, and do **not**
claim that the upstream AI model is reproducible.

---

## 1. Methods — reproducible implementation

> All post-detection processing — record merging and quality control, trajectory
> speed flagging, 100 m grid construction, observation-exposure aggregation,
> effective-coverage screening, 3 m seed-radius spatial deduplication, normalized
> intensity and recurrence calculation, period-stability analysis, and the
> management-priority classification — was implemented as a sequence of
> configuration-driven Python scripts. Parameters (grid size, deduplication
> radius, effective-coverage threshold, period boundaries and priority
> percentiles) are held in a single configuration file, and intermediate outputs
> are written at each stage so that the full set of analytical tables and figures
> can be regenerated from equivalently-structured inputs. The code is openly
> available (see Code Availability) together with a synthetic example that
> exercises the entire workflow without any restricted data.

## 2. Code Availability Statement

> A version-controlled repository containing the downstream post-detection
> analytical pipeline — including quality control, exposure correction,
> deduplication, indicator construction, temporal stability analysis, and priority
> classification, with a synthetic worked example and unit tests — will be archived
> on Zenodo after the first GitHub release. The pipeline was verified to reproduce
> the reported spatial outputs at the level of individual grid cells on the
> restricted study data. The upstream AI detection model is proprietary to its
> operator and is not included.

## 3. Data Availability Statement

> The raw second-by-second trajectory records, road images, bounding-box images
> and precise georeferenced detections are restricted by municipal operational
> information and by the service provider's proprietary materials and cannot be
> made public. De-identified, cell-level analytical outputs that underlie the
> main tables and figures may be shared subject to written permission from Aioi
> City and Pirika, Inc.; until then they are available from the corresponding
> author upon reasonable request under the same permissions. The analysis code is
> openly available (see Code Availability).

## 4. Scope statement — proprietary detector vs. open downstream pipeline

> This study analyses the outputs of an already-deployed, vehicle-mounted AI
> road-litter detection system (Takanome, operated by Pirika, Inc.). The internal
> architecture, training data, confidence thresholds and filtering logic of the
> detection model are proprietary to the operator and were not available to the
> authors; they are neither reproduced nor distributed here. The contribution of
> this work, and of the released code, is the **downstream** post-detection
> analytical pipeline: it takes time-stamped, georeferenced detection records and
> non-detection trajectory points and converts them into exposure-normalized,
> recurrence-aware, management-ready municipal indicators. Detector reliability is
> characterized empirically through independent manual validation rather than by
> inspecting the model.

## 5. Cover-letter paragraph

> To support transparency and reproducibility, the downstream post-detection
> analytical pipeline developed in this study — including public configuration
> templates, unit tests and a synthetic worked example — will be openly released
> through GitHub and archived on Zenodo after the first GitHub release. The
> resulting DOI will be added to the manuscript and related submission materials.
> We note that the upstream AI detection model is a proprietary third-party system
> that was not available to us and is therefore not part of the release; the
> released code covers the analytical methodology we developed. The restricted raw
> trajectory and image data cannot be made public for municipal-operational and
> proprietary reasons, as stated in the Data Availability Statement.

---

*After the first GitHub release is archived on Zenodo, insert the repository URL
and the resulting DOI into the Code Availability and Data Availability statements
(see `zenodo_release_checklist.md`).*
