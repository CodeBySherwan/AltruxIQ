import json
from pathlib import Path
from datetime import datetime

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
        self._load_custom_materials()

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
            
# --- NEW METHODS BELOW ---

    def _load_custom_materials(self):
        self.custom_path = self.db_path.parent / "custom_materials.json"
        try:
            with open(self.custom_path, 'r') as f:
                self.custom_materials = json.load(f)
        except FileNotFoundError:
            self.custom_materials = []

    @property
    def all_materials(self):
        """Returns standard + custom materials in one list."""
        return self.materials + self.custom_materials

    def add_custom_material(self, material_dict: dict):
        """Appends a new custom material and persists to disk."""
        material_dict["is_custom"] = True
        material_dict["created_at"] = datetime.now().isoformat()
        self.custom_materials.append(material_dict)
        self._save_custom_materials()

    def delete_custom_material(self, name: str) -> bool:
        """Removes a custom material by exact name match."""
        original_count = len(self.custom_materials)
        self.custom_materials = [
            m for m in self.custom_materials if m["Material"] != name
        ]
        if len(self.custom_materials) < original_count:
            self._save_custom_materials()
            return True
        return False

    def _save_custom_materials(self):
        with open(self.custom_path, 'w') as f:
            json.dump(self.custom_materials, f, indent=4)