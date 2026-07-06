"""AltruxIQ exception hierarchy — single source for domain-specific errors.

Catch :class:`AltruxIQError` to handle any app-originated error; catch a
subclass to handle a specific category. Solver and validation code should
raise these instead of bare ``ValueError`` / ``RuntimeError`` so the CLI
layer can distinguish user-fixable problems (bad input, under-constrained
model) from genuine programming bugs (``AttributeError`` / ``KeyError`` /
``NameError``) that should propagate.

Hierarchy::

    Exception
    └── AltruxIQError
        ├── ValidationError
        │   └── SectionGeometryError
        ├── SolverError
        │   └── SingularStiffnessMatrixError
        └── PersistenceError
"""
from __future__ import annotations


class AltruxIQError(Exception):
    """Base for every exception AltruxIQ raises on purpose."""


class ValidationError(AltruxIQError):
    """User-supplied input is invalid or internally inconsistent.

    Covers bad geometry (non-positive dimensions, inner >= outer), malformed
    segment definitions, and over/under-constrained structures. Recoverable:
    the user can re-enter data and retry.
    """


class SectionGeometryError(ValidationError):
    """A cross-section's dimensions are physically impossible or inconsistent.

    Raised by the MOI solver when a profile violates a geometric constraint
    (e.g. web thicker than flange, inner diameter not less than outer).
    """


class SolverError(AltruxIQError):
    """The numerical solver failed to produce a result."""


class SingularStiffnessMatrixError(SolverError):
    """Global stiffness matrix is singular — the structure is a mechanism.

    Typically means supports are insufficient or badly placed so the system
    retains a rigid-body mode. Distinct from :class:`ValidationError` because
    the individual inputs may each be valid; the failure is numerical.
    """


class PersistenceError(AltruxIQError):
    """Saving or loading a project file failed."""
