"""Beam-domain input wizards for AltruxIQ.

One convenient import surface for the interactive beam-definition wizards:
structural classification, geometry/supports, loads, and stepped segments.
These are the domain wizards that drive the stage-by-stage project setup in
``ui.cli``; the generic prompt toolkit they are built on lives in
``ui.console``, and material selection lives in ``ui.materials``.

Extracted from ``ui.inputs`` during the P3 ``ui/beam/`` decomposition
(checkpoint-3). Pure relocation; signatures and behavior unchanged.
"""
from ui.beam.classification import (
    Beam_Classification,
    get_solver_resolution,
)
from ui.beam.geometry import (
    Beam_Length,
    Beam_Supports,
    define_continuous_supports,
    define_custom_supports,
)
from ui.beam.loads import manage_loads
from ui.beam.stepped import (
    define_stepped_segments,
    define_segment_lengths,
    define_segment_section,
    define_segment_material,
    assemble_segments,
    validate_segments_for_solve,
)

__all__ = [
    "Beam_Classification",
    "get_solver_resolution",
    "Beam_Length",
    "Beam_Supports",
    "define_continuous_supports",
    "define_custom_supports",
    "manage_loads",
    # Stepped Bar — legacy monolith (retired in P6 checkpoint-B) + per-stage helpers
    "define_stepped_segments",
    "define_segment_lengths",
    "define_segment_section",
    "define_segment_material",
    "assemble_segments",
    "validate_segments_for_solve",
]
