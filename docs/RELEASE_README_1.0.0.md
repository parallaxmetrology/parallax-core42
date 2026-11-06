> **Historical record.** This is the README of the 1.0.0 release candidate (3 September 2026), kept unchanged for lineage. The current README is at the repository root; the licence statement at the end below was superseded on 6 November 2026 (see `NOTICE.md`).

# Parallax Core 42 v1.0.0

Parallax Core 42 is a deterministic patch-level measurement instrument for RGB
histology images. It emits 42 named scalar measurements describing soft gradients,
operational nuclear blobs, luminance and chromatic boundary fields, multiscale
geometry, orientation organization, and radial compliance.

This is a clean software release of the fixed 42-axis panel shared by the verified
TCGA/HER2/HTAN persistence work and the later CAMELYON/CPTAC assays. It is not a
copy of the historical notebooks. It removes notebook state, absolute paths, batch
sampling, labels, fitted classifiers, survival models, and implicit reference data.

## The contract

- Input: one 8-bit RGB patch, or a directory of RGB images.
- Preprocessing: longest edge is reduced to at most 512 pixels; smaller inputs are
  not enlarged. Optional fixed-Macenko preprocessing is explicit and separate.
- Output: 14 provenance/status fields followed by the frozen 42 axes.
- Randomness: none in the measurement path.
- Training: none in the measurement path.
- Reference cohorts: none in the measurement path.
- Physical resolution: supplied by the study protocol, not inferred by the package.

The absence of trained parameters in this extractor does not make a downstream
classifier “training-free.” Any LDA, regression, reference standardization,
compartment definition, or outcome model must be described and versioned separately.

## Install

From this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Or install the bundled validated wheel after installing the listed dependencies:

```bash
python -m pip install dist/parallax_core42-1.0.0-py3-none-any.whl
```

`requirements-lock.txt` records the exact direct dependency versions used for the
release tests, and `validation/BUILD_ENVIRONMENT.json` records the interpreter and
platform. `pyproject.toml` supplies bounded ranges for ordinary installation.

## Measure a patch or directory

```bash
parallax-core42 image.png --output measurements.csv
parallax-core42 patches/ --recursive --output measurements.jsonl
```

Optional normalization with the preserved corrected target:

```bash
parallax-core42 patches/ --recursive \
  --macenko-target references/tcga_fixed_macenko_target.json \
  --output measurements_normalized.csv
```

Normalization is not enabled by default. The included target reproduces one recent
experimental path; it is not a universal stain standard and does not establish
preparation invariance.

Python API:

```python
from parallax_core42 import AXES, measure_path

row = measure_path("image.png")
assert row["status"] == "ok"
values = [row[axis] for axis in AXES]
```

The v1.0 constants are frozen. Passing a modified `ExtractorConfig` raises an error;
parameter changes require a newly named schema and fresh known-answer record.

## Validate

```bash
PYTHONPATH=src python validate_release.py --check-only
shasum -a 256 -c MANIFEST_SHA256.txt
```

The release contains a validated installable wheel; a synthetic, non-biological fixture; raw and fixed-Macenko
known-answer outputs; unit and CLI tests; and a source-equivalence record. On the
frozen fixture, all 42 axes reproduce the archived v4.1 kernel at tolerance 1e-12,
with maximum absolute difference 0.0 in the release environment.

## Read before interpreting

1. `docs/AXIS_DICTIONARY.md` and `.csv` define every output and its units.
2. `docs/SCOPE_AND_BOUNDARIES.md` states what the package does not claim.
3. `docs/PREPROCESSING_AND_SCALE.md` describes normalization and physical scale.
4. `docs/PROVENANCE.md` maps this release to the verified historical source.
5. `validation/RELEASE_VALIDATION.json` records the executable checks.

`RELEASE.json` provides the same release identity and source hashes in a compact
machine-readable form.

`PARALLAX_CORE42_RELEASE_GUIDE.html` combines the main documentation into one
self-contained, browser-readable document.

## Omega naming

Core 42 retains the historical column name `omega` for mask-centroid disagreement.
It does **not** calculate the separate historical quantity also called Omega: distance
from class-conditional or cohort structural norms. Reference-dependent deviation is
outside this release and should receive a distinct name in any future package.

## Research status

This is research software, not a medical device. It does not diagnose tissue,
predict prognosis, establish specimen identity, or validate biological mechanisms.
Its outputs are sensitive to crop, resolution, orientation, stain, preparation,
tissue composition, and sampled extent. Those sensitivities are properties to test
and document, not nuisances the package silently removes.

No redistribution license has yet been assigned. See `NOTICE.md` before public
release or third-party redistribution.
