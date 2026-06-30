"""Common path utilities for AltruxIQ."""

import os
import sys


def ensure_src_in_path():
    """
    Ensure the project src/ directory is in sys.path.

    This is called from modules inside src/ to allow cross-package imports
    (e.g.  from solver.stepped_solver import …  from a file under src/ui/).
    """
    # This file lives at  src/common/paths.py
    # Two levels up gives the src/ folder.
    src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
