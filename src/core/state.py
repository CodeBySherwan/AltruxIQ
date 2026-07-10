import numpy as np
from dataclasses import dataclass, field
from typing import Any
from common.units import METRIC_UNITS
from common.config import SOLVER

@dataclass
class ProjectState:
    """
    Centralized session state for AltruxIQ.
    Replaces ~30 module-level global variables in cli.py.
    """
    # --- UI & Environment State ---
    current_unit_system: str = "Metric"
    current_labels: dict = field(default_factory=lambda: METRIC_UNITS)
    beam_storage: list = field(default_factory=list)
    current_project: dict | None = None
    Materials: Any = None
    SectionsDB: Any = None
    
    project_state: dict = field(default_factory=lambda: {
        "is_loaded": False,
        "profile_saved": False, 
        "material_saved": False,
        "loads_saved": False,
        "supports_saved": False,
        "has_unsaved_changes": False
    })
    
    # --- Beam Geometry & Supports ---
    beam_length: float = 0.0
    A: float = 0.0
    B: float = 0.0
    A_restraint: list = field(default_factory=list)
    B_restraint: list = field(default_factory=list)
    A_type: str = ""
    B_type: str = ""
    support_types: tuple = ("pin", "roller")
    beam_type: str | None = None
    supports_list: list = field(default_factory=list)
    segments: list = field(default_factory=list)
    
    # --- Material Properties ---
    selected_material: str = ''
    elastic_modulus: float = 0.0
    density: float = 0.0
    yield_strength: float = 0.0
    ultimate_strength: float = 0.0
    poisson_ratio: float = 0.0
    
    # --- Cross-Section Properties ---
    shape: str = ""
    Ix: float = 0.0
    c: float = 0.0
    b: float = 0.0
    y_array: np.ndarray = field(default_factory=lambda: np.array([]))
    section_dims: dict = field(default_factory=dict)
    
    # --- Loads ---
    loads: dict = field(default_factory=dict)
    pointloads: list = field(default_factory=list)
    distributedloads: list = field(default_factory=list)
    momentloads: list = field(default_factory=list)
    triangleloads: list = field(default_factory=list)
    
    # --- Analysis Results ---
    num_points: int = SOLVER.DEFAULT_NUM_POINTS
    X_Field: np.ndarray = field(default_factory=lambda: np.array([]))
    Total_ShearForce: np.ndarray = field(default_factory=lambda: np.array([]))
    Total_BendingMoment: np.ndarray = field(default_factory=lambda: np.array([]))
    Reactions: np.ndarray = field(default_factory=lambda: np.array([]))
    
    Deflection: Any = None
    Slope: Any = None
    Slopes: Any = None
    Curvatures: Any = None
    Shear_stress: Any = None
    bending_stress: Any = None
    FOS: Any = None
    AxialForce: Any = None
    AxialDisplacement: Any = None

# Singleton state object to be imported across the application
state = ProjectState()
