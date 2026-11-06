# Preprocessing and physical scale

## Core image handling

The extractor converts files to RGB and reduces the longest image edge to the
configured ceiling, 512 pixels by default, using Pillow Lanczos resampling. It does
not enlarge smaller images. Non-square images retain their aspect ratio.

In Core 42 v1.0 the 512-pixel ceiling and all measurement constants are frozen, not
user-tunable command-line settings. A changed constant requires a new schema.

Core 42 does not select tissue, reject background, sample a whole slide, or infer
micrometres per pixel. Those operations determine what the patch represents and must
be frozen in the study protocol.

## Physical resolution

Several measurements use fixed pixel scales. Blob radii use sigma 6–20 pixels;
multiscale orientation uses sigmas 1, 8, and 32 pixels; adaptive morphology and
minimum-object thresholds also act in pixel units. Comparisons across datasets are
physically interpretable only when patch resolution and field of view are controlled
or explicitly studied.

For the recent persistence experiments, the dominant standardized arm measured
512×512-pixel fields at 0.50 micrometres per pixel. That study convention is not
hard-coded into Core 42.

## Stain normalization

The optional `FixedMacenkoNormalizer` is the corrected mean-centred covariance
implementation used in the recent verification programme. The historical
uncentred-SVD implementation was mathematically degenerate and is not included.

Normalization is intentionally a separate step because:

- it changes several measurement axes;
- it requires an explicit target;
- it does not remove all site, scanner, preparation, composition, or extent signal;
- raw and normalized measurements can answer different audit questions.

The bundled target records the matrix and concentration values used in the recent
TCGA-derived path. It is included for reproducibility, not promoted as a universal
reference. A new study may fit another target, but must preserve that target and
must not compare results as if the references were interchangeable.

## Recommended paired assay

When technical sensitivity is part of the question, retain parallel arms:

1. raw RGB input;
2. explicitly normalized input;
3. simple grayscale or edge controls;
4. recorded crop, physical scale, scanner, site, preparation, and slide extent.

This makes technical and structural channels inspectable rather than assuming that
normalization has erased them.
