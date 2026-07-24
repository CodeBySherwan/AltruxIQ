"""Post-processing navigation menus: results/visualization and the
PyVista 3D FEA contour sub-menu.

Extracted from ``ui.Menus`` during the P3 ``ui/menus/`` decomposition
(checkpoint-5). Pure relocation; signatures and behavior unchanged.
"""
from termcolor import colored

from ui.console import clear_screen
def postprocessing_menu(beam_type=None):
    """Display an enhanced postprocessing/visualization menu and return the user's choice."""
    clear_screen()
    
    # Create a decorative header
    print("\n")
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║                POSTPROCESSING/VISUALIZATION                  ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    print("\n")
    
    # Create a visually distinct menu with icons and better formatting
    print(colored("┌─ VISUALIZATION OPTIONS "+"─"*38, 'yellow', attrs=['bold']))
    
    menu_items = [
        ("🔄 Reactions Schematic Plots",         "Visualize support reaction forces (Plotly-only)"),
        ("📊 Shear-Force Plots",                 "Generate SFD diagram"),
        ("📊 Bending-Moment Plot",               "Generate BMD diagram"),
        ("📊 Shear-Force/Bending-Moment Plots",  "Generate SFD and BMD diagrams"),
        ("📈 Shear-Stress",                      "Display Shear stress distribution"),
        ("📈 Bending-Stress",                    "Display Bending stress distribution"),
        ("📉 Deflection Plots",                  "Show beam displacement curves"),
        ("📑 Combined Plots",                    "Show all diagrams together (Plotly Only)"),
    ]
    
    # Stepped bar extras
    if beam_type == "Stepped Bar":
        menu_items.append(("📈 Axial-Force Plot",       "Display axial force diagram"))
        menu_items.append(("📈 Axial-Displacement Plot", "Display axial displacement diagram"))
        menu_items.append(("📈 Combined Stress",         "Display combined bending + axial stress"))
    
    menu_items.append(("🧱 3D FEA Contour View",       "Commercial FEA-style 3D coloured contour plots (PyVista)"))
    menu_items.append(("⬅️  Return to Main Menu",      "Go back to the main menu"))
    
    for idx, (title, description) in enumerate(menu_items, 1):
        print(colored(f"│ {idx:2d} │ {title}", 'yellow') + 
              colored(f" - {description}", 'white'))
    
    print(colored("└───" + "─"*57, 'yellow', attrs=['bold']))
    
    # Get user input with improved prompt
    print("")
    max_choice = len(menu_items)
    choice = input(colored(f"Enter your choice [1-{max_choice}] ➔ ", 'cyan', attrs=['bold']))
    return choice
def pyvista_menu():
    """Display the PyVista 3D FEA contour sub-menu and return the user's choice."""
    clear_screen()

    print("\n")
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║            3D FEA CONTOUR VIEW  (PyVista)                    ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    print("\n")
    print(colored("┌─ SELECT RESULT TO VISUALISE "+"─"*33, 'yellow', attrs=['bold']))

    menu_items = [
        ("🔄 Reactions Schematic",    "Reaction force arrows on 3D beam solid"),
        ("📊 Shear Force",            "Blue→Red shear force contour on 3D beam"),
        ("📊 Bending Moment",         "Blue→Red bending moment contour on 3D beam"),
        ("📈 Shear Stress",           "Blue→Red shear stress contour on 3D beam"),
        ("📈 Bending Stress",         "Blue→Red bending stress contour on 3D beam"),
        ("📉 Deflection",             "Displaced shape coloured by displacement magnitude"),
        ("📑 Combined (All Results)", "Sequential viewer — close each window to advance"),
        ("🎬 Load Animation",         "Watch the beam deflect & load from 0% → 100% (animated)"),
        ("⬅️  Return to Postprocessing Menu", "Go back"),
    ]

    for idx, (title, description) in enumerate(menu_items, 1):
        print(colored(f"│ {idx:2d} │ {title}", 'yellow') +
              colored(f" - {description}", 'white'))

    print(colored("└───" + "─"*57, 'yellow', attrs=['bold']))
    print(colored("""
  ℹ  Screenshots are automatically saved to  screenshots/  folder.
  ℹ  Close the interactive window to return to the menu.
""", 'cyan'))
    print("")
    choice = input(colored("Enter your choice [1-9] ➔ ", 'cyan', attrs=['bold']))
    return choice
