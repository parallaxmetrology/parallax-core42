"""Frozen output schema for Parallax Core 42 v1.0.0."""

from __future__ import annotations


VERSION = "1.0.0"
SCHEMA_ID = "parallax-core42-1.0.0"

AXES = (
    "gap_rv",
    "gap_theta",
    "gap_delta_vs_baseline",
    "gap_ds",
    "blob_density",
    "blob_size_mean",
    "blob_size_cv",
    "k_rv",
    "k_mu",
    "k_sdi",
    "k_rho",
    "k_xp",
    "k_theta",
    "k_ds",
    "b_rv",
    "b_mu",
    "b_sdi",
    "b_rho",
    "b_xp",
    "b_theta",
    "b_ds",
    "omega",
    "gamma",
    "delta_r",
    "beta",
    "g1_len",
    "g1_curv",
    "g2_V",
    "g2_n",
    "g2_AR",
    "g2_cut",
    "g3_kvar",
    "g3_infl",
    "g4_s1",
    "g4_s8",
    "g4_s32",
    "g4_slope",
    "sci",
    "vcli_g",
    "rc_f",
    "rc_s",
    "drc",
)

FAMILIES = {
    "gap": AXES[0:4],
    "nuclear_blob": AXES[4:7],
    "confirmed_kernel": AXES[7:14],
    "baseline_kernel": AXES[14:21],
    "relational": AXES[21:25],
    "multiscale_geometry": AXES[25:37],
    "composite": AXES[37:39],
    "radial_compliance": AXES[39:42],
}

METADATA_COLUMNS = (
    "schema_id",
    "source_id",
    "status",
    "warning",
    "image_hash",
    "original_width_px",
    "original_height_px",
    "measured_width_px",
    "measured_height_px",
    "resize_long_edge_px",
    "confirmed_empty",
    "g4_scale_collapse",
    "degenerate_masks",
    "n_valid_masks",
)

OUTPUT_COLUMNS = METADATA_COLUMNS + AXES


def validate_schema() -> None:
    """Raise if the frozen schema has been changed inconsistently."""
    if len(AXES) != 42:
        raise RuntimeError(f"Expected 42 axes, found {len(AXES)}")
    if len(set(AXES)) != len(AXES):
        raise RuntimeError("Axis names are not unique")
    flattened = tuple(axis for axes in FAMILIES.values() for axis in axes)
    if flattened != AXES:
        raise RuntimeError("Family order does not reconstruct the frozen axis order")


validate_schema()
