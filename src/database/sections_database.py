import json
from pathlib import Path
from datetime import datetime

class SectionsDatabase:
    def __init__(self):
        # Safely resolve paths relative to this file's location
        project_root = Path(__file__).resolve().parent.parent.parent
        self.standard_path = project_root / "data" / "standard_sections.json"
        self.custom_path = project_root / "data" / "custom_sections.json"
        
        self.standard_sections = {}
        self.custom_sections = []
        
        self._load_standard()
        self._load_custom()

    def _load_standard(self):
        try:
            with open(self.standard_path, 'r') as f:
                self.standard_sections = json.load(f)
        except FileNotFoundError:
            self.standard_sections = {}

    def _load_custom(self):
        try:
            with open(self.custom_path, 'r') as f:
                self.custom_sections = json.load(f)
        except FileNotFoundError:
            self.custom_sections = []

    def get_standard_families(self) -> list[str]:
        return list(self.standard_sections.keys())

    def get_sections_in_family(self, family: str) -> list[dict]:
        return self.standard_sections.get(family, [])

    def save_custom_section(self, section_dict: dict):
        section_dict["created_at"] = datetime.now().isoformat()
        self.custom_sections.append(section_dict)
        self._save_custom()

    def delete_custom_section(self, name: str) -> bool:
        original_count = len(self.custom_sections)
        self.custom_sections = [s for s in self.custom_sections if s["name"] != name]
        if len(self.custom_sections) < original_count:
            self._save_custom()
            return True
        return False

    def list_custom_sections(self) -> list[dict]:
        return self.custom_sections

    def _save_custom(self):
        self.custom_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.custom_path, 'w') as f:
            json.dump(self.custom_sections, f, indent=2)