# src/solver/area_solver.py
"""
AltruxIQ — Cross-Sectional Area Solver
========================================
Computes cross-sectional area A (m²) from the canonical section_dims dict
produced by moi_solver.py. Every shape supported by the MOI solver has a
matching area formula here.

All dimensions are expected in SI units (meters).
"""

import numpy as np
import os
import sys

from common.exceptions import SectionGeometryError

def area_from_section(shape: str, section_dims: dict) -> float:
    """
    Compute cross-sectional area A (m²) from section dimensions.

    Parameters
    ----------
    shape : str
        Canonical shape name (matches moi_solver.py output).
    section_dims : dict
        Shape-specific geometry dict (matches moi_solver.py output).

    Returns
    -------
    float
        Cross-sectional area in m².

    Raises
    ------
    SectionGeometryError
        If the shape is not recognised or its dimensions are missing/invalid.
    """
    if not section_dims or not isinstance(section_dims, dict):
        raise SectionGeometryError("section_dims must be a non-empty dict.")

    # -----------------------------------------------------------------------
    # 1. I-beam
    # -----------------------------------------------------------------------
    if shape == "I-beam":
        bf = section_dims.get('bf', 0.0)
        tf = section_dims.get('tf', 0.0)
        hw = section_dims.get('hw', 0.0)
        tw = section_dims.get('tw', 0.0)
        if any(v <= 0 for v in (bf, tf, hw, tw)):
            raise SectionGeometryError("I-beam dimensions must all be positive.")
        return 2.0 * bf * tf + tw * hw

    # -----------------------------------------------------------------------
    # 2. T-beam
    # -----------------------------------------------------------------------
    elif shape == "T-beam":
        bf = section_dims.get('bf', 0.0)
        tf = section_dims.get('tf', 0.0)
        hw = section_dims.get('hw', 0.0)
        tw = section_dims.get('tw', 0.0)
        if any(v <= 0 for v in (bf, tf, hw, tw)):
            raise SectionGeometryError("T-beam dimensions must all be positive.")
        return bf * tf + hw * tw

    # -----------------------------------------------------------------------
    # 3. Solid Circle
    # -----------------------------------------------------------------------
    elif shape in ("Circle", "Solid Circle"):
        r = section_dims.get('radius', 0.0)
        if r <= 0:
            raise SectionGeometryError("Circle radius must be positive.")
        return np.pi * r ** 2

    # -----------------------------------------------------------------------
    # 4. Hollow Circle
    # -----------------------------------------------------------------------
    elif shape == "Hollow Circle":
        ro = section_dims.get('r_outer', 0.0)
        ri = section_dims.get('r_inner', 0.0)
        if ro <= 0 or ri <= 0 or ri >= ro:
            raise SectionGeometryError("Hollow Circle: 0 < r_inner < r_outer required.")
        return np.pi * (ro ** 2 - ri ** 2)

    # -----------------------------------------------------------------------
    # 5. Rectangle
    # -----------------------------------------------------------------------
    elif shape == "Rectangle":
        width = section_dims.get('width', 0.0)
        height = section_dims.get('height', 0.0)
        if width <= 0 or height <= 0:
            raise SectionGeometryError("Rectangle dimensions must be positive.")
        return width * height

    # -----------------------------------------------------------------------
    # 6. Square
    # -----------------------------------------------------------------------
    elif shape == "Square":
        side = section_dims.get('side', 0.0)
        if side <= 0:
            raise SectionGeometryError("Square side length must be positive.")
        return side ** 2

    # -----------------------------------------------------------------------
    # 7. Hollow Square
    # -----------------------------------------------------------------------
    elif shape == "Hollow Square":
        B = section_dims.get('outer_width', 0.0)
        b = section_dims.get('inner_width', 0.0)
        if B <= 0 or b <= 0 or b >= B:
            raise SectionGeometryError("Hollow Square: 0 < inner_width < outer_width required.")
        return B ** 2 - b ** 2

    # -----------------------------------------------------------------------
    # 8. Hollow Rectangle
    # -----------------------------------------------------------------------
    elif shape == "Hollow Rectangle":
        outer_b = section_dims.get('outer_b', 0.0)
        outer_h = section_dims.get('outer_h', 0.0)
        inner_b = section_dims.get('inner_b', 0.0)
        inner_h = section_dims.get('inner_h', 0.0)
        if any(v <= 0 for v in (outer_b, outer_h, inner_b, inner_h)):
            raise SectionGeometryError("Hollow Rectangle dimensions must all be positive.")
        if inner_b >= outer_b or inner_h >= outer_h:
            raise SectionGeometryError("Hollow Rectangle: inner must be smaller than outer.")
        return outer_b * outer_h - inner_b * inner_h

    # -----------------------------------------------------------------------
    # Fallback
    # -----------------------------------------------------------------------
    else:
        raise SectionGeometryError(
            f"Unknown shape: '{shape}'. "
            f"Supported: I-beam, T-beam, Circle, Hollow Circle, "
            f"Rectangle, Square, Hollow Square, Hollow Rectangle."
        )
