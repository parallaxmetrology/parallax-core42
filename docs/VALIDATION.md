# Validation protocol

Run from the release root:

```bash
PYTHONPATH=src python validate_release.py --check-only
shasum -a 256 -c MANIFEST_SHA256.txt
```

Omit `--check-only` only when intentionally regenerating the deterministic
`validation/RELEASE_VALIDATION.json` record before rebuilding the manifest.

The validator checks:

- exactly 42 unique axes and frozen family order;
- exact output-column order;
- frozen fixture SHA-256;
- every raw known-answer axis within the numerical tolerance;
- axis dictionary identity and completeness;
- 42-of-42 equivalence against the archived v4.1 source on both the bundled
  synthetic fixture and a non-bundled real H&E verification tile;
- the pinned optional normalization target;
- pixel-identical optional normalization against its archived implementation;
- absence of machine-specific paths, class labels, and reference-dependent Omega
  logic from executable package code;
- unit, deterministic-repeat, normalized known-answer, and CLI tests.
- wheel construction, isolated-target installation, and byte-identical CLI output.

The synthetic fixture is not histology and cannot validate biological meaning. It is
deliberately redistributable and exists only to exercise the numerical path.

The direct dependency versions are recorded in `requirements-lock.txt`; interpreter
and platform details are in `validation/BUILD_ENVIRONMENT.json`. Broader versions
admitted by `pyproject.toml` are convenience ranges, not evidence of exact
cross-version numerical identity. Rebuild the known-answer validation whenever the
environment changes.
