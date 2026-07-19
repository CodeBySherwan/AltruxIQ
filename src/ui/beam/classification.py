"""Beam classification and solver-resolution wizards.

Interactive prompts that define the analysis problem itself: which beam
idealisation (support topology / determinacy) the solver will run, and at
what solver resolution. Both are small "define the problem" wizards, which
is why ``get_solver_resolution`` lives here alongside
``Beam_Classification`` rather than in its own module (placement decision
recorded for P3 checkpoint-3).

Extracted from ``ui.inputs`` during the P3 ``ui/beam/`` decomposition
(checkpoint-3). Pure relocation; signatures and behavior unchanged.
"""
import time
from termcolor import colored

from common.config import SOLVER
from ui.console import (print_error, clear_screen, ui_banner,
                        ui_open, ui_close, ui_blank)
from ui.console.prompts import ask_int

#  Beam Classification Setup


def Beam_Classification():
    """Prompt the user to select a structural system (beam idealisation)
    with schematic previews and determinacy notes. Returns the internal
    beam-type keyword expected by the solver/controller."""
    clear_screen()
    ui_banner("STAGE 1  \u2014  STRUCTURAL SYSTEM",
              "Select the beam idealisation & support topology", color='cyan')

    systems = [
        ("1", "Simple Supported Beam", "Statically determinate",
         "\u25b3 \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500 \u25cb   (pin \u2014 roller)"),
        ("2", "Overhanging Beam", "Statically determinate",
         "\u2500\u2500 \u25b3 \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500 \u25cb \u2500\u2500   (cantilevered ends)"),
        ("3", "Cantilever Beam", "Statically determinate",
         "\u2503\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501   (fixed \u2014 free)"),
        ("4", "Fixed\u2013Fixed Beam", "Indeterminate (3\u00b0)",
         "\u2503\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2503   (fixed \u2014 fixed)"),
        ("5", "Propped Cantilever", "Indeterminate (1\u00b0)",
         "\u2503\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501 \u25cb   (fixed \u2014 roller)"),
        ("6", "Continuous Beam", "Indeterminate (multi-span)",
         "\u25b3 \u2500\u2500\u2500\u2500 \u25cb \u2500\u2500\u2500\u2500 \u25cb \u2500\u2500\u2500\u2500 \u25cb"),
        ("7", "Custom Beam", "User-defined supports",
         "? \u2500\u2500\u2500\u2500 ? \u2500\u2500\u2500\u2500 ? \u2500\u2500\u2500\u2500 ?"),
        ("8", "Stepped Bar", "Varying cross-section / material",
         "\u2550\u2501\u2501\u2550\u2501\u2501\u2550\u2501\u2501\u2550   (axial + bending)"),
    ]

    print("\n")
    ui_open("SELECT BEAM TYPE", 'yellow')
    ui_blank('yellow')
    for num, name, determ, schematic in systems:
        print(colored(f"\u2502 {num} \u2502 ", 'yellow')
              + colored(name.ljust(24), 'yellow', attrs=['bold'])
              + colored(determ, 'cyan'))
        print(colored("\u2502     \u2192 ", 'yellow') + colored(schematic, 'white'))
        ui_blank('yellow')
    ui_close('yellow')

    print("")
    classification = input(colored("  Enter your choice [1-8] \u2794 ", 'cyan', attrs=['bold']))

    mapping = {
        '1': "Simple", '2': "Overhanging Beam", '3': "Cantilever",
        '4': "Fixed-Fixed", '5': "Propped", '6': "Continuous", '7': "Custom",
        '8': "Stepped Bar",
    }
    if classification in mapping:
        return mapping[classification]
    print_error("Invalid selection. Please choose a number between 1 and 8.")
    time.sleep(1.5)
    return Beam_Classification()

#--------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------

def get_solver_resolution():
    """
    Prompt the user to enter a custom solver resolution between 201 and 10001.
    """
    return ask_int("Enter custom solver resolution",
                   minimum=SOLVER.MIN_NUM_POINTS, maximum=SOLVER.MAX_NUM_POINTS,
                   default=SOLVER.DEFAULT_NUM_POINTS, allow_cancel=True)
