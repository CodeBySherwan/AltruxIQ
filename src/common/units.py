"""Centralized unit handling for AltruxIQ — single source of truth.

Label dicts, SI<->display conversion factors, JSON storage-schema factors,
and batch scaling helpers. All internal computation is base SI; conversion
happens only at display/input boundaries via :func:`get_divisor` /
:func:`to_si`, and at the persistence boundary via :func:`to_json` /
:func:`from_json` (materials JSON stores strength in MPa / modulus in GPa,
not base-SI Pa).

Supported quantities: length, length_small, force, moment, area, inertia,
sec_mod, modulus, stress, density, distributed.

This module supersedes the previously duplicated unit code in:
  - ``ui/Menus.py``    (METRIC_UNITS, IMPERIAL_UNITS, get_divisor)
  - ``ui/cli.py``      (former METRIC_LABELS / IMPERIAL_LABELS alias — removed,
                        now imports METRIC_UNITS / IMPERIAL_UNITS directly)
  - ``ui/inputs.py``   (CONVERSION_TO_SI, hardcoded 16.01846/6.894757/0.006894757)
  - ``solver/moi_solver.py`` (get_moi_scale parallel engine — deleted)
  - ``plotting/main_plotting.py`` (_get_scale)
Each of those now re-exports or calls into this module.
"""
from collections import namedtuple

# ---------------------------------------------------------------------------
# Display labels per quantity (canonical)
# ---------------------------------------------------------------------------
METRIC_UNITS = {
    'length': 'm',
    'length_small': 'mm',
    'force': 'N',
    'moment': 'N·m',
    'area': 'm²',
    'inertia': 'm⁴',
    'sec_mod': 'm³',
    'modulus': 'GPa',
    'density': 'kg/m³',
    'stress': 'MPa',
}

IMPERIAL_UNITS = {
    'length': 'ft',
    'length_small': 'in',
    'force': 'lbf',
    'moment': 'lbf·ft',
    'area': 'ft²',
    'inertia': 'in⁴',
    'sec_mod': 'in³',
    'modulus': 'ksi',
    'density': 'lb/ft³',
    'stress': 'ksi',
}

UNIT_SYSTEMS = {"Metric": METRIC_UNITS, "Imperial": IMPERIAL_UNITS}
DEFAULT_UNITS = METRIC_UNITS

# ---------------------------------------------------------------------------
# One factor table that drives BOTH conversion engines
# ---------------------------------------------------------------------------
# Convention: 1 display-unit = FACTOR × SI-unit
#   ⇒  SI_value     = display_value * FACTOR   (use to_si / system_multiplier)
#   ⇒  display_value = SI_value      / FACTOR   (use from_si / get_divisor)
# Reproduces the old Menus.get_divisor AND inputs.CONVERSION_TO_SI exactly,
# adding 'distributed' to the divisor side and the remaining quantities
# (length_small, modulus, stress, density, inertia, sec_mod) to the multiplier side.
_SI_FACTORS = {
    "Metric": {
        'length': 1.0,
        'length_small': 1e-3,        # m -> mm
        'force': 1.0,
        'moment': 1.0,
        'area': 1.0,
        'inertia': 1.0,
        'sec_mod': 1.0,
        'modulus': 1e9,              # Pa -> GPa
        'stress': 1e6,               # Pa -> MPa
        'density': 1.0,
        'distributed': 1.0,
    },
    "Imperial": {
        'length': 0.3048,            # ft -> m
        'length_small': 0.0254,      # in -> m
        'force': 4.4482216,          # lbf -> N
        'moment': 1.3558179,         # lbf·ft -> N·m
        'area': (0.3048) ** 2,       # ft² -> m²
        'inertia': (0.0254) ** 4,    # in⁴ -> m⁴
        'sec_mod': (0.0254) ** 3,    # in³ -> m³
        'modulus': 6894757.29,       # ksi -> Pa
        'stress': 6894757.29,        # ksi -> Pa
        'density': 16.01846,         # lb/ft³ -> kg/m³
        'distributed': 14.5939,      # lbf/ft -> N/m
    },
}


def is_imperial(units_dict):
    """True when the active units dict represents the Imperial system."""
    return units_dict.get('length') == 'ft'


def _system_key(units_dict):
    """Resolve a units dict (or a system string) to a canonical 'Metric'/'Imperial' key."""
    if isinstance(units_dict, str):
        return "Imperial" if units_dict.lower().startswith("imp") else "Metric"
    return "Imperial" if is_imperial(units_dict) else "Metric"


def default_units():
    """Return a fresh copy of the default (Metric) units dict."""
    return dict(DEFAULT_UNITS)


def get_divisor(units_dict, quantity):
    """SI -> display divisor.  ``display_value = SI_value / get_divisor(units, quantity)``.

    Backward-compatible signature with the legacy ``ui.Menus.get_divisor``.
    """
    return _SI_FACTORS[_system_key(units_dict)].get(quantity, 1.0)


def from_si(units_dict, quantity, value):
    """Convert a base-SI value into the active display unit."""
    return value / get_divisor(units_dict, quantity)


def to_si(units_dict, quantity, value):
    """Convert a value given in the active display unit into base SI."""
    return value * _SI_FACTORS[_system_key(units_dict)].get(quantity, 1.0)


# ---------------------------------------------------------------------------
# JSON storage-schema factors
# ---------------------------------------------------------------------------
# The materials JSON stores density in kg/m³ (= SI), but strength in MPa and
# modulus in GPa — NOT base SI (Pa). So the display→JSON factor differs from
# the display→SI factor by 1e6 (stress) or 1e9 (modulus). This table captures
# that storage convention separately from _SI_FACTORS so the two semantics
# (display↔SI vs display↔JSON) stay distinct and explicit.
# Convention: 1 JSON-unit = FACTOR × display-unit  (mirrors _SI_FACTORS)
_JSON_FACTORS = {
    "Metric": {
        'density': _SI_FACTORS["Metric"]['density'],          # 1.0  (kg/m³ display == kg/m³ JSON)
        'stress':  _SI_FACTORS["Metric"]['stress']  / 1e6,    # 1.0  (MPa display == MPa JSON)
        'modulus': _SI_FACTORS["Metric"]['modulus'] / 1e9,    # 1.0  (GPa display == GPa JSON)
    },
    "Imperial": {
        'density': _SI_FACTORS["Imperial"]['density'],        # 16.01846
        'stress':  _SI_FACTORS["Imperial"]['stress']  / 1e6,  # 6.894757
        'modulus': _SI_FACTORS["Imperial"]['modulus'] / 1e9,  # 0.006894757
    },
}


def to_json(units_dict, quantity, value):
    """Convert a display-unit value into the JSON storage schema unit."""
    return value * _JSON_FACTORS[_system_key(units_dict)].get(quantity, 1.0)


def from_json(units_dict, quantity, value):
    """Convert a JSON-stored value back into the active display unit."""
    return value / _JSON_FACTORS[_system_key(units_dict)].get(quantity, 1.0)


def system_multiplier(unit_system, quantity):
    """display -> SI factor, keyed by the system string ('Metric'/'Imperial').

    Drop-in replacement for the legacy ``inputs.CONVERSION_TO_SI[system][quantity]``.
    """
    return _SI_FACTORS[_system_key(unit_system)].get(quantity, 1.0)


# ---------------------------------------------------------------------------
# Batch helper for plotting (replaces plotting/main_plotting.py::_get_scale)
# ---------------------------------------------------------------------------
UnitScale = namedtuple(
    "UnitScale",
    ["units", "length", "length_small", "force", "moment", "stress"],
)


def get_scale(units):
    """Batch divisor helper.

    Returns a :class:`UnitScale` namedtuple ``(units, length, length_small,
    force, moment, stress)`` carrying the SI->display divisor for each of the
    quantities most plotting functions need in one call.

    Positional-compatible with the legacy ``main_plotting._get_scale`` 6-tuple,
    **but** ``.stress`` is the real STRESS divisor (the old code wrongly used
    ``'length_small'`` here, which made every stress diagram off by ~1e9).
    """
    if units is None:
        units = default_units()
    return UnitScale(
        units,
        get_divisor(units, 'length'),
        get_divisor(units, 'length_small'),
        get_divisor(units, 'force'),
        get_divisor(units, 'moment'),
        get_divisor(units, 'stress'),
    )
