"""Centralized application constants for AltruxIQ — single source of truth.

Solver defaults, resolution bounds, serviceability limits, and engineering
targets. Nothing in the codebase should hardcode these numbers — import the
``SOLVER`` / ``SERVICEABILITY`` instances (or the dataclasses) from here
instead of re-typing the literals.

Companion to :mod:`common.paths` and :mod:`common.units`; same conventions:
all values are in base SI unless noted, and the dataclasses are frozen so the
constants cannot be mutated at runtime.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class SolverDefaults:
    """Numerical defaults shared by the FEA solvers and the resolution menu."""

    # Output-grid resolution (number of evaluation points along the beam).
    DEFAULT_NUM_POINTS: int = 2001

    # Bounds enforced by the solver-resolution prompt / menu.
    MIN_NUM_POINTS: int = 201
    MAX_NUM_POINTS: int = 10001

    # Minimum sub-elements per distributed / triangular load span in the
    # stepped-bar FEM mesh (stepped_solver.MIN_LOAD_ELEMS).
    MIN_LOAD_SUBDIVISIONS: int = 100

    # Fallback elastic properties used when a caller omits E / I. Steel-like
    # values; matches the historical indeterminate_solver defaults.
    FALLBACK_STEEL_E_PA: float = 210e9    # Young's modulus, Pascals
    FALLBACK_STEEL_I_M4: float = 8.33e-6  # Second moment of area, m^4


@dataclass(frozen=True)
class ServiceabilityLimits:
    """Deflection (span/deflection) denominators and the target FoS.

    Each float ``D`` represents the ``D`` in an ``L / D`` serviceability
    criterion — e.g. ``GENERAL_FLOOR = 360.0`` means the governing limit is
    ``L / 360``. Compare a span_ratio ``δ / L`` against ``1 / D``.
    """

    ROOF_NO_CEILING: float = 240.0    # L/240  — roof members, no ceiling
    GENERAL_FLOOR: float = 360.0      # L/360  — general / floors (governing)
    BRITTLE_FINISHES: float = 480.0   # L/480  — members supporting brittle finishes
    CANTILEVER_LIMIT: float = 180.0   # L/180  — cantilever excessive-deflection hard limit
    VERY_STIFF_TIER: float = 500.0    # L/500  — "very stiff" verdict tier

    # Target strength reserve for the design-check / recommendation reports.
    TARGET_FACTOR_OF_SAFETY: float = 1.50


# Import-friendly singleton instances.
SOLVER: SolverDefaults = SolverDefaults()
SERVICEABILITY: ServiceabilityLimits = ServiceabilityLimits()
