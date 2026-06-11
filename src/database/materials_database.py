import json
from pathlib import Path

class MaterialDatabase:
    def __init__(self, filename="materials.Json"):
        # 1. Get the absolute path of THIS script (.../src/database/materials_database.py)
        current_script_path = Path(__file__).resolve()
        
        # 2. Navigate up the directory tree to the project root
        # .parent goes up one level. 
        # current_script_path.parent == .../src/database
        # current_script_path.parent.parent == .../src
        # current_script_path.parent.parent.parent == project_root
        project_root = current_script_path.parent.parent.parent
        
        # 3. Construct the absolute path to the data file
        # pathlib uses the '/' operator to elegantly join paths
        self.db_path = project_root / 'data' / filename
        
        # 4. Open the file using the robust absolute path
        try:
            with open(self.db_path, 'r') as file:
                self.materials = json.load(file)
        except FileNotFoundError:
            # Provide a helpful error message for debugging
            print(f"CRITICAL ERROR: Could not find database at {self.db_path}")
            raise

    def search_by_property(self, property_name, min_value=0, max_value=float('inf')):
        """Search materials by property within min and max limits."""
        results = [
            material for material in self.materials
            if property_name in material and min_value <= material.get(property_name, -1) <= max_value
        ]
        return results

    def list_all_materials(self):
        """List all material names."""
        return [material["Material"] for material in self.materials]

    def print_materials(self, materials_list):
        """Nicely print materials from a given list."""
        for material in materials_list:
            print(f"- {material['Material']}:")
            for key, value in material.items():
                if key != "Material":
                    print(f"   {key}: {value}")
            print()