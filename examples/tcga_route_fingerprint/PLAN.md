# Core42 route fingerprint (worked example for the public release), written 2026-11-06 before any measurement

**Question.** Does the frozen Core42 panel, with no labels, show how TCGA-COAD diagnostic slides were produced? Image only: no outcome, survival, clinical or label data are read.

**Groups (known in advance, from TCGA_PRODUCTION_ROUTES_20261104 / SITE_RESOLUTION_20261104):**
- `AA-regular`: site AA, MIRAX scans converted to SVS (95 patients);
- `AA-derivative`: site AA, the small derivative files (15 patients with tiles; listed in parallaxmetrology/he-checks);
- `other-sites`: sites A6, AZ, AY, 5M, 4T, Aperio-native scans (71 patients).

The AA-regular vs AA-derivative contrast holds tissue source site fixed and changes only the production route. The other-sites contrast mixes route and site.

**Tiles.** Kather et al. 2020 TCGA tile archive (Zenodo 3784345), 512 px tumour-region tiles. Per patient: 8 tiles drawn with numpy default_rng(20261106) over sorted member names, skipping tiles with mean RGB ≥ 220 (blank). Patients with fewer than 4 usable tiles are reported and dropped.

**Measurement.** parallax-core42 1.0.0, two arms: raw RGB, and the bundled fixed-Macenko target. Status != ok rows are counted and dropped. Patient value = median of each axis over its tiles.

**Analyses, all fixed now:**
1. Per-axis patient-level AUC (Mann–Whitney, no fitting) for AA-regular vs AA-derivative and AA-regular vs other-sites, both arms; report |AUC − 0.5| ranking and the count of axes with AUC ≥ 0.8 or ≤ 0.2.
2. Unsupervised: PCA on patient medians (standardised over all patients, a fitted transform named as such), first two components plotted by group; no labels used to fit.
3. A named fitted readout as a secondary: shrinkage LDA, leave-one-patient-out, three-group balanced accuracy, both arms.
4. Report the normalised arm next to raw, to show what normalisation does and does not remove.

**Reading.** Descriptive. This uses groups already known to differ; it demonstrates what the panel exposes and is not a test of a new hypothesis. No threshold decides a pass.
