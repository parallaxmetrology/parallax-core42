# How it compares

Every result below is from a study whose specification was written before the data were opened, unless it is marked post hoc. Each is the 42 axes **plus a named fitted readout or test**; the axes themselves contain no fitted parameters. Full write-ups: [Transport tests note](https://www.parallaxmetrology.com/Transport_Tests_NOTE.html), [claim ledger](https://www.parallaxmetrology.com/Parallax_Pathology_Claim_Ledger.html).

## 1. As a feature block next to colour (two pre-registered tests)

Readout in both: training-only standardisation, then shrinkage linear discriminant analysis with equal priors. No tuning, feature selection or pretrained encoder. Core42 was measured after a corrected fixed-target Macenko normalisation; colour summaries on the unnormalised image.

### Camelyon17-WILDS, tumour vs non-tumour patches (24 slides, 5 hospitals, 11,996 patches)

Slide-averaged AUROC:

| representation | random patches | slide regions | held-out slides | held-out hospitals |
|---|---|---|---|---|
| colour summaries | 0.875 | 0.847 | 0.858 | 0.818 |
| Core42 alone | 0.856 | 0.827 | 0.849 | 0.826 |
| colour + Core42 | 0.918 | 0.891 | 0.903 | 0.865 |
| grayscale texture | 0.914 | 0.896 | 0.907 | **0.900** |

- Adding Core42 to colour raised AUROC by +0.044, +0.045 and +0.046 for slide regions, held-out slides and held-out hospitals (99% intervals +0.004 to +0.092, +0.014 to +0.077, +0.003 to +0.094). The gain is about the same size under every split.
- That met **one of four** pre-registered pass conditions. The other three (a graded difficulty ladder, structure degrading differently from colour, a rank swap) were not met.
- Post hoc: 20 within-hospital column shuffles of the 42 axes all lowered AUROC; no single family (geometry, relational, optical/kernel) carried the gain on its own.
- **A plain grayscale-texture family beat Core42 alone in every split, and beat colour + Core42 on held-out hospitals (0.900 against 0.865)** and slightly on regions and slides. Core42 is complementary to colour, not a better descriptor than ordinary texture.

### CPTAC clear-cell renal carcinoma, low vs high grade, patient-held (79 patients, 158 slides, 10,112 fields)

| representation | patient AUROC |
|---|---|
| colour summaries | 0.651 |
| Core42 alone | 0.577 |
| colour + Core42 | 0.628 |
| grayscale texture | 0.683 |

Adding Core42 to colour changed AUROC by −0.023 (95% interval −0.085 to +0.031). Neither pre-registered rule was met and the branch closed as specified.

**Reading the pair.** Complementary to colour for patch-level tumour detection, including across hospitals; nothing detectable for weakly supervised patient-level grading. An operating window, not a general claim.

## 2. As a fingerprint of a section (related-section retrieval)

These ask whether the 42 axes recognise the same piece of tissue again. Retrieval compares per-slide or per-section distributions of the axes (robust standardisation fitted on the gallery only, then quantile summaries and nearest-neighbour ranking). The HTAN rows used the bundled corrected normaliser.

| study | result |
|---|---|
| TCGA-COAD, two non-overlapping sets of 50 tiles from the same slide (174 slides) | top-1 retrieval 89.1%, top-5 98.9% |
| same, with a hard geographic split between the two sets | top-1 38.5%, top-5 67.8% (median separation 0.58 of the slide diagonal) |
| HTAN, 14 tissue pieces, related serial sections | mean reciprocal rank 0.796, top-1 73.8% (artefact-controlled) |
| HTAN, six four-section series with reported depth | distance rises with reported section separation, Spearman ρ 0.45 (p 0.008) |

Boundaries the audit attached:
- Same-slide linkability includes shared slide preparation and local geography. It is section identity, not patient invariance.
- Registered point-by-point agreement between same-portion sections was **not** detected (p 0.19); the persistence is distributional, not positional.
- On HTAN, normalised colour summaries track reported depth too (ρ 0.65), and source stain parameters drift with depth; the structural response is not isolated from depth-associated processing.
- A DLPFC brain serial-section test was null.

## 3. As a provenance detector

The same sensitivity that makes Core42 recognise a section makes it record how the section was produced. In the studies above that showed up repeatedly:

- **CPTAC slide extent.** Same-patient slide retrieval with Core42 was partly carried by gross whole-slide size: a four-number extent description alone retrieved paired slides (mean reciprocal rank 0.627 against 0.282 chance), and adjusting for extent reduced Core42's retrieval from 0.720 to 0.576 (67% of its excess over chance remained).
- **Site.** Corrected stain normalisation did not remove tissue-source-site structure from TCGA-COAD measurements.
- **Production route.** The worked example in [`examples/tcga_route_fingerprint/`](../examples/tcga_route_fingerprint/) measures TCGA-COAD tiles from three production routes with no labels in the measurement.

This is the use the repository is organised around: if your cohort splits by site, scanner, route or preparation, Core42 is likely to show it, and it will show *which named axes* do the splitting. It does not flag per-slide artefacts (blur, folds, pen marks); [HistoQC](https://github.com/choosehappy/HistoQC) does that, and the two are complementary.

## What is not claimed

No diagnostic, prognostic or clinical claim; no claim that Core42 beats learned features or foundation models (it does not); no stain, scanner or rotation invariance. Earlier survival results from the wider Parallax Pathology programme were retracted or bounded in the claim ledger and are not part of this release.
