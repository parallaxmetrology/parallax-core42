# Parallax Core 42 axis dictionary

The machine-readable authority is `AXIS_DICTIONARY.csv`. The 42 columns are emitted
in the frozen order defined by `parallax_core42.schema.AXES`.

## Families

| Family | Axes | Purpose |
|---|---:|---|
| Gap | 4 | Soft-gradient activity not retained by the Canny boundary mask |
| Nuclear blob | 3 | Operational hematoxylin-channel DoG detections |
| Confirmed kernel | 7 | Geometry of luminance edges confirmed by an L–M opponent field |
| Baseline kernel | 7 | Geometry of the LAB-L gradient-magnitude field |
| Relational | 4 | Disagreement among mask locations and activation extents |
| Multiscale geometry | 12 | Centroid paths, void regions, contour variation, and scale-dependent orientation entropy |
| Composite | 2 | Fixed heuristic combinations of several measurements |
| Radial compliance | 3 | Agreement with frame- and structure-centered radial decay models |

## Two meanings historically called Omega

The `omega` column in Core 42 is the mean pairwise distance among centroids of
eligible mask fields. It is a patch measurement and requires no reference cohort.

Some historical Parallax documents also used “Omega” for a separate,
reference-dependent distance from class or cohort norms. That quantity is not part
of Core 42. A future reference layer may calculate it from selected Core 42 axes,
but it must use a separately versioned reference file and a distinct output name.

## Units and scale

Most outputs are dimensionless operational indices. Pixel-valued blob sizes and
fixed Gaussian scales only have comparable physical meaning when input resolution
is controlled. The extractor records image dimensions and its resize ceiling, but
it does not infer micrometres per pixel. Whole-slide sampling and physical-scale
harmonization belong to the study protocol.

## Orientation and crop dependence

Several axes are deliberately frame-relative. Peripheral mass, centroid paths,
orientation coherence, and some composites can change with rotation, reflection,
translation, or crop choice. Core 42 is deterministic; it is not geometrically
invariant. Such transformations should be prespecified controls when relevant.
