# Zenodo release checklist

Work top-to-bottom. Do **not** make the repository public or mint a DOI until
every sensitive-data item is checked.

## 1. Sensitive-information sweep (before making the repo public)
- [ ] No raw second-by-second GPS trajectory files anywhere in the repo.
- [ ] No raw or bounding-box road images.
- [ ] No precise real coordinates; no real cell-centre coordinates that could
      reconstruct routes (the only coordinates present are the **synthetic**
      example's fictional values).
- [ ] No real dates, real device IDs, or device→route correspondences.
- [ ] No municipal collection-schedule or operational information.
- [ ] No proprietary detector internals (architecture, training data, thresholds,
      filtering logic).
- [ ] No personal data (license plates, pedestrians, residences).
- [ ] No absolute local paths, machine usernames, API tokens, credentials, or
      email signatures in code, configs, notebooks, or commit history.
- [ ] `examples/expected_output/` contains only synthetic-derived files.
- [ ] `TO_REVIEW_BEFORE_PUBLIC_RELEASE/` contains **no** real data (only the
      README and the review checklist).
- [ ] `git log -p` and `git grep` scanned for accidental secrets / real data.

## 2. Repository hygiene
- [ ] `LICENSE` (MIT) present at repo root.
- [ ] `docs/DATA_AND_DOCUMENTATION_LICENSE.md` (CC-BY-4.0 for docs and future
      de-identified derived data) present, clearly stating that **raw data are
      not** released under CC-BY.
- [ ] `CITATION.cff` present with authors (Zenodo DOI added after archival).
- [ ] `requirements.txt` / `environment.yml` reproduce the environment.
- [ ] `README.md` complete; synthetic example runs end-to-end.
- [ ] `python -m pytest tests/ -q` passes.

## 3. GitHub release
- [ ] Push to a **public** GitHub repository (only after section 1 passes).
- [ ] Create a tagged release, e.g. `v1.0.0`.

## 4. Zenodo archival
- [ ] Enable the Zenodo–GitHub integration for the repository.
- [ ] Publish the GitHub release; Zenodo archives the tagged snapshot.
- [ ] Obtain the version DOI and the concept (all-versions) DOI.

## 5. Wire the DOI back in
- [ ] Insert the minted Zenodo DOI into `README.md`, `CITATION.cff`, the
      manuscript **Code Availability Statement**, and the cover letter.
- [ ] Record the code version ↔ manuscript version mapping in `CHANGELOG.md`.

## 6. Provenance record
- [ ] Note the git tag, commit hash and Zenodo DOI together with the manuscript
      revision they correspond to (keep with the submission package).
