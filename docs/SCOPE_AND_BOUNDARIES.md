# Scope and claim boundaries

## What Core 42 is

Core 42 is a fixed deterministic mapping from an RGB image patch to 42 scalar
measurements. The mapping contains no fitted model, class label, reference cohort,
outcome, random sampling, or patient information.

The word “deterministic” means that the same decoded pixels, configuration, software
environment, and numerical platform should produce the same output within the
recorded tolerance. It does not mean that different crops, scanners, compression
levels, stains, orientations, or library versions are guaranteed to agree.

## What it is not

Core 42 is not:

- a classifier;
- a training-free diagnostic system;
- a survival biomarker;
- a stain-invariant representation;
- a rotation-, translation-, or crop-invariant representation;
- a cell segmentation or nucleus-counting system;
- a whole-slide sampler;
- an implementation of structural address compartments;
- a patient or specimen identification product;
- a medical device.

Downstream supervised readouts, reference distances, spatial compartments, and
whole-slide aggregation are distinct analytical layers. They must be trained or
defined only within the appropriate training data and evaluated with grouped,
patient-separated, and site-aware designs when the task requires them.

## Relationship to the evidence programme

The 42-axis panel is the frozen common measurement block used across the verified
section-persistence line and later external assays. Other programme results used
additional or differently summarized measurements:

- the historical “58-axis” language referred to a broader notebook-era frame;
- EBHI and STHELAR structural-address experiments used study-specific 45-summary
  compartment representations;
- raw-color, grayscale, and simple-edge controls are separate representations;
- reference-dependent deviation scores and fitted LDA models are separate layers.

This release therefore anchors one stable measurement object. It does not claim to
be a single executable reproduction of every historical analysis.

## Required reporting

Every study using Core 42 should report:

1. package version and manifest hash;
2. input patch dimensions and physical resolution, if known;
3. crop and tissue-selection procedure;
4. raw versus normalized input status and normalizer target hash;
5. image orientation or augmentation policy;
6. aggregation, scaling, imputation, and fitted readout;
7. patient, slide, site, and batch separation rules;
8. failed measurements and non-finite-value handling.

The v1.0 constants are locked in executable code. A parameter change is a derivative
instrument and must receive a new schema identifier, axis dictionary, and validation
record.
