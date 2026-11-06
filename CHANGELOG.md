# Changelog

## 1.0.0 public repository (2026-11-06)

Packaging only; measurement code, constants, fixtures and validation records are unchanged
(the validator and the source-file hashes confirm it).

- MIT licence for code, CC BY 4.0 for documentation (`NOTICE.md`).
- New README for the public repository; the original release README is kept at
  `docs/RELEASE_README_1.0.0.md`.
- Added `docs/HOW_IT_COMPARES.md`, `docs/KNOWN_ISSUES.md` and a worked provenance
  example in `examples/tcga_route_fingerprint/`.
- Added `examples/fingerprint_cohort.py` (a provenance report for any cohort) and `tests/test_examples.py`.
- Added CI, issue templates and package metadata; rebuilt `MANIFEST_SHA256.txt`.

## 1.0.0 — 2026-09-03

- Established the frozen 42-axis patch-measurement schema.
- Locked all v1.0 numerical constants; changed parameters require a new schema.
- Removed notebook, path, cohort, label, reference, and fitted-model dependencies.
- Separated optional corrected fixed-Macenko preprocessing from measurement.
- Added a complete machine-readable axis dictionary.
- Added raw and normalized known-answer fixtures, CLI tests, source-equivalence
  adjudication, independent release validation, and SHA-256 manifesting.
- Documented the two historical meanings of Omega and excluded the
  reference-dependent meaning from this release.
