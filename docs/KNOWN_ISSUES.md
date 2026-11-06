# Known issues and things to know before using it

The axis-by-axis cautions are in [AXIS_DICTIONARY.csv](AXIS_DICTIONARY.csv). These are the ones most likely to matter.

## Measurement behaviour (frozen by design)

1. **Not invariant to the frame.** `k_xp`, `b_xp`, centroid paths (`g1_*`), orientation axes (`*_theta`, `g4_*`) and the composites change with rotation, reflection, translation and crop. If orientation is arbitrary in your data, make rotation a prespecified control.
2. **Pixel units, not microns.** Blob sigmas (6–20 px), G4 sigmas (1, 8, 32 px) and morphology thresholds act in pixels after the 512-px long-edge ceiling. Comparing datasets at different µm/px compares different physical scales. Core42 does not read or infer pixel spacing; see [PREPROCESSING_AND_SCALE.md](PREPROCESSING_AND_SCALE.md). Some public slides have wrong stated spacing ([he-checks](https://github.com/parallaxmetrology/he-checks)).
3. **Several names overstate what is computed.** `blob_density` is a DoG detection rate on the haematoxylin channel, not a nucleus count. `g3_infl` is a sign-change density, not an inflection count. `k_mu` / `b_mu` were called cohesion historically; they are a mass-concentration fraction. `omega` here is mask-centroid disagreement, not the reference-based deviation that earlier Parallax documents also called Omega.
4. **Two composites carry hard-coded constants.** `sci` uses fixed v4.1 weights and `vcli_g` uses fixed v4.1 reference means and scales. They are deterministic, but those constants were chosen during development; treat them as operational scores, not calibrated indices.
5. **Empty and degenerate fields.** Very pale or very uniform patches can leave the confirmed field empty or the G4 scales collapsed. The `status`, `warning`, `confirmed_empty`, `g4_scale_collapse` and `degenerate_masks` columns record this; filter on them before summarising.
6. **The g1 and g3 axes are computed as named.** A sibling instrument from the same lineage ([structural-topology-kernel](https://github.com/parallaxmetrology/structural-topology-kernel/blob/main/docs/known-issues.md)) takes differences with `np.diff(x, 0)`, which returns positions instead of steps. Core42 uses `np.diff(..., axis=0)` and does not have that defect.

## Stain normalisation

7. **Off by default, and it changes several axes.** The optional fixed-Macenko step is the corrected, mean-centred implementation. The degenerate uncentred version used in early Parallax work (its H and E vectors collapsed to 0.17° apart) is not included. Raw and normalised measurements answer different questions; keep both arms when technical sensitivity matters.
8. **The bundled target is one TCGA-derived reference,** kept for reproducibility. It is not a universal standard, and normalising does not remove site structure ([HOW_IT_COMPARES.md](HOW_IT_COMPARES.md), section 3).

## Interpretation

9. **It records how tissue was handled as well as what it is.** That is why it is useful for provenance, and it is also why any biological or clinical reading needs site-, scanner- and batch-aware designs. A grouping found by Core42 is a lead to explain, not a cause.
10. **Plain texture is often stronger.** In both pre-registered tests a grayscale-texture family outperformed the 42 axes for classification. Use Core42 for named, inspectable structure and provenance, not to maximise accuracy.

## Packaging

11. The measurement source is the frozen v1.0 release reproduced from the historical v4.1 kernel (42/42 axes, maximum difference 0.0). It is kept byte-for-byte rather than reformatted, so style linters will report findings in `src/`; changing it would require a new schema.
12. Python 3.11+.
