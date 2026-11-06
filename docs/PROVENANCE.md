# Provenance and reconstruction record

## Frozen source

The numerical source for Core 42 is the archived v4.1 kernel:

- historical filename: `parallax_pathology_v41.py`
- historical SHA-256: `b6fc19229b98f854c95bfcb1c3ebb8040cd935303ec1be0cbf1349d14d30a43e`
- reconstructed release: `parallax-core42` version 1.0.0
- reconstruction date: 3 September 2026

The 42-axis order is the frozen `STRUCTURAL_AXES` list used by the verified Degas,
TCGA cross-slide, TCGA same-portion, HER2-ST, HTAN, CAMELYON, and CPTAC analyses.

## What was retained

The release retains the numerical definitions required to calculate the 42 axes:

- sRGB linearization, LAB-L and cone transforms;
- fixed H&E deconvolution matrix;
- gradient and opponent masks;
- kernel, relational, multiscale, blob, composite, and radial calculations;
- the 512-pixel default resize ceiling and v4.1 constants.

## What was removed

The release excludes material not required by the 42-axis measurement contract:

- Colab and notebook state;
- machine-specific paths;
- TCGA zip discovery and patient sampling;
- class labels and outcome data;
- GLCM and tonal outputs outside the frozen 42-axis panel;
- the ambiguous reference-dependent Omega engine;
- fitted classifiers, cohort scaling, retrieval, and survival analysis;
- the historical degenerate Macenko implementation.

Optional corrected Macenko normalization is provided as a separate module. Its
bundled target is copied numerically from `stage2_normalizer.json`, source SHA-256
`d2f71ff6bb3d02f86f3d2700a394a1a28fb89adb907258afb1f3b30de2b983ef`.
The clean normalizer was also compared against `LOCAL_PIPELINE/run_batch.py`, source
SHA-256 `566bdb05ae2bf92d52d450d3bd0eab64e42784554066859d903e713c6bc4d6ff`.
On the frozen fixture, all 786,432 RGB channel values were identical.

## Compatibility edits

Deprecated scikit-image aliases were replaced with their current equivalents. The
new `max_size` threshold was chosen to reproduce the historical strict
“remove objects smaller than minimum size” behavior. Region-property aliases were
updated without changing the calculation.

## Numerical adjudication

`scripts/verify_against_historical_source.py` loaded the archived source independently
and compared all 42 outputs on both the frozen synthetic fixture and a real TCGA H&E
tile already held in the verification archive. Both comparisons produced 42 of 42
axes matching at relative and absolute tolerance 1e-12, with maximum absolute
difference 0.0. The real tile is not duplicated in this software packet; its SHA-256
is preserved in the validation record. The historical source is not required after
installation; the self-contained synthetic known-answer fixture guards subsequent
runs.

This proves implementation equivalence for the tested input and environment. It does
not prove equivalence on every possible image, biological validity, external
performance, or stability under future dependency versions.
