"""Navigation menus for the AltruxIQ FEA workflow.

One convenient import surface for the 14 navigation menus, grouped by
workflow stage: main/project management, pre-processing, solution,
post-processing and configuration.

Extracted from ``ui.Menus`` during the P3 ``ui/menus/`` decomposition
(checkpoint-5). Pure relocation; signatures and behavior unchanged.
"""
from ui.menus.main import (
    main_menu_template,
    project_management_menu,
)
from ui.menus.preprocessing import (
    profile_definition_menu,
    choose_profile,
    profile_source_menu,
    display_section_library,
    material_selection_menu,
    boundary_conditions_menu,
    loads_definition_menu,
)
from ui.menus.solution import analysis_simulation_menu
from ui.menus.postprocessing import (
    postprocessing_menu,
    pyvista_menu,
)
from ui.menus.config import (
    unit_system_menu,
    resolution_menu,
)
__all__ = [
    # main
    "main_menu_template",
    "project_management_menu",
    # pre-processing
    "profile_definition_menu",
    "choose_profile",
    "profile_source_menu",
    "display_section_library",
    "material_selection_menu",
    "boundary_conditions_menu",
    "loads_definition_menu",
    # solution
    "analysis_simulation_menu",
    # post-processing
    "postprocessing_menu",
    "pyvista_menu",
    # configuration
    "unit_system_menu",
    "resolution_menu",
]
