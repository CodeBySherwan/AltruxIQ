"""Solution-stage navigation menu (analysis / simulation).

Extracted from ``ui.Menus`` during the P3 ``ui/menus/`` decomposition
(checkpoint-5). Pure relocation; signatures and behavior unchanged.
"""
from termcolor import colored

from ui.console import clear_screen
def analysis_simulation_menu():
    """Display an enhanced analysis/simulation menu and return the user's choice."""
    clear_screen()
    
    # Create a decorative header
    print("\n")
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║                  ANALYSIS/SIMULATION                         ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    print("\n")
    
    # Create a visually distinct menu with icons and better formatting
    print(colored("┌─ OPTIONS "+"─"*52, 'yellow', attrs=['bold']))
    
    menu_items = [
        ("🧮 Solve Beam", "Calculate shear force, bending moment, and reactions"),
        ("📈 View Analysis Results", "Display the calculated beam response"),
        ("📉 Calculate Deflection", "Compute beam deflection under loads"),
        ("⚠️  Calculate Stress and F.O.S", "Determine stresses and factor of safety"),
        ("⬅️  Return to Main Menu", "Go back to the main menu")
    ]
    
    for idx, (title, description) in enumerate(menu_items, 1):
        print(colored(f"│ {idx:2d} │ {title}", 'yellow') + 
              colored(f" - {description}", 'white'))
    
    print(colored("└───" + "─"*57, 'yellow', attrs=['bold']))
    
    # Get user input with improved prompt
    print("")
    choice = input(colored("Enter your choice [1-5] ➔ ", 'cyan', attrs=['bold']))
    return choice
