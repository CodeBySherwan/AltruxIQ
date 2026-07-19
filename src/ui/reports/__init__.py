"""Domain report renderers for AltruxIQ analysis results.

One convenient import surface for the post-solution reports: analysis
summary, static-solution results, deflection/serviceability, stress/FoS
and the engineering design-check recommendations dossier.

Extracted from ``ui.Menus`` during the P3 ``ui/reports/`` decomposition
(checkpoint-4). Pure relocation; signatures and behavior unchanged.
"""
from ui.reports.analysis_report import (
    display_analysis_info,
    display_analysis_results,
)
from ui.reports.deflection_report import display_deflection_analysis
from ui.reports.stress_report import display_stress_analysis
from ui.reports.recommendations_report import display_engineering_recommendations

__all__ = [
    "display_analysis_info",
    "display_analysis_results",
    "display_deflection_analysis",
    "display_stress_analysis",
    "display_engineering_recommendations",
]
