"""Configuration navigation menus: unit system and solver resolution.

Extracted from ``ui.Menus`` during the P3 ``ui/menus/`` decomposition
(checkpoint-5). Pure relocation; signatures and behavior unchanged.
"""
from termcolor import colored

from ui.console import clear_screen
# =============================
#  UNIT SYSTEM SELECTION 
# ============================
def unit_system_menu(current_system="Metric"):
    """Display the unit configuration options and return choice."""
    clear_screen()
    print("\n")
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║                    UNIT SYSTEM SELECTION                     ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    print("\n")
    
    print(colored("┌─ OPTIONS "+"─"*52, 'yellow', attrs=['bold']))
    print(colored("│ 1  │ 🌍 Metric System (SI)", 'yellow') + colored(" - Meters, Newtons, MPa, GPa", 'white'))
    print(colored("│ 2  │ 🦅 US Customary / Imperial", 'yellow') + colored(" - Feet/Inches, lbf, ksi", 'white'))
    print(colored("│ 3  │ ⬅️  Return to Main Menu", 'yellow') + colored(" - Keep current configuration", 'white'))
    print(colored("└───" + "─"*57, 'yellow', attrs=['bold']))
    
    print("\n" + colored("┌─ ACTIVE SYSTEM ", 'green') + colored("─"*46, 'green', attrs=['bold']))
    print(colored(f"│ Current Setting: {current_system}", 'green'))
    print(colored("└───" + "─"*53, 'green', attrs=['bold']))
    
    print("")
    choice = input(colored("Select your unit system [1-3] ➔ ", 'cyan', attrs=['bold']))
    return choice
    #-----------------------------------------------------------------------------------
    #-----------------------------------------------------------------------------------
def resolution_menu(current_points):
    """Display the solver resolution options."""
    clear_screen()
    print("\n")
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║                   SOLVER RESOLUTION                          ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    print("\n")
    print(colored("┌─ OPTIONS "+"─"*52, 'yellow', attrs=['bold']))
    print(colored(f"│ Current setting: {current_points} points", 'white', attrs=['bold']))
    print(colored("├" + "─"*61, 'yellow'))
    print(colored("│ 1  │ Fast Draft   (501)", 'yellow') + colored("  — Best for multi-span beams", 'white'))
    print(colored("│ 2  │ Standard    (1001)", 'yellow') + colored("  — Balanced speed and accuracy", 'white'))
    print(colored("│ 3  │ High        (2001)", 'yellow') + colored("  — Default", 'white'))
    print(colored("│ 4  │ Fine        (5001)", 'yellow') + colored("  — Report-quality smooth curves", 'white'))
    print(colored("│ 5  │ Custom            ", 'yellow') + colored("  — Enter a value (201 - 10001)", 'white'))
    print(colored("│ 6  │ ⬅️  Return to Main Menu", 'yellow'))
    print(colored("└───" + "─"*57, 'yellow', attrs=['bold']))
    print(colored("\n  ⚠ Higher values significantly increase solve time for\n    Continuous and indeterminate beams (SymPy evaluation).", 'cyan'))
    print("")
    choice = input(colored("Enter your choice [1-6] ➔ ", 'cyan', attrs=['bold']))
    return choice
    #---------------------------------------------------------------------------
    #---------------------------------------------------------------------------
