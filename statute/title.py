import json
from pathlib import Path
from typing import Optional
from statute import Statute 

class Title:

    def __init__(self, statutes: list[Statute]):
        self.statutes = statutes

        self.reference_registry: dict[str, Statute] = {}
        for statute in statutes:
            key = self._make_registry_key(statute.reference)
            if key in self.reference_registry:
                raise ValueError(f"Duplicate statute reference: {key}")
            self.reference_registry[key] = statute

    def _make_registry_key(self, ref: dict) -> str:
        """Create a unique key from a section reference dict."""
        version = ref.get("version") or ""
        return f"{ref['title'].lower()}|{ref['section'].lower()}|{version.lower()}"

    def get_reference_text(self, section_reference: dict, subsection_reference: str = "", **kwargs) -> Optional[str]:
        """
        Given a section reference and a subsection path (e.g., "A.1.b"),
        return the referenced text or None if not found.
        """
        key = self._make_registry_key(section_reference)

        statute = self.reference_registry.get(key)
        if not statute:
            return None
        
        return statute.get_text(subsection=subsection_reference, **kwargs)

    def save_cache(self, cache_path: Path):
        """Save the title (list of statutes) to a JSON cache file."""
        data = {
            "statutes": [s.to_json() for s in self.statutes],
        }
        cache_path.write_text(json.dumps(data, indent=2))

    @staticmethod
    def from_cache(cache_path: Path) -> "Title":
        """Load a title from a JSON cache file."""
        raw = json.loads(cache_path.read_text())

        statutes = [Statute.from_json(json.loads(s)) for s in raw["statutes"]]
        return Title(statutes)
