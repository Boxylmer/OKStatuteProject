import json
from pathlib import Path
from typing import Iterator, Union, Literal

from statute.reference import StatuteReference

class Statute:
    """Main class that holds statute information."""

    SCHEMA_VERSION = 1  # In case you want versioning support

    def __init__(self, reference: StatuteReference, name: str, body: dict, history):
        self.reference = reference  # {"reference": title, "section": section, "version": version or None}

        self.name = name
        self.body = body
        # looks like this
        # {'label': '', 'text': 'Baz', 'subsections': [{'label': 'A', 'text': 'Foo', 'subsections': []}, {'label': 'B', 'text': 'Bar', 'subsections': []}]}
        # if contains references, looks like
        #   {'label': '', 'text': 'Baz', 'subsections': [
        #       {'label': 'A', 'text': 'Foo', 'subsections': [], 'references'=[]},
        #       {'label': 'B', 'text': 'Bar', 'subsections': [], 'references'=[]}
        #    ], 'references'=[]}

        self.history = history

    def directory(self) -> list[str]:
        def collect_labels(sections, prefix=""):
            labels = []
            for section in sections:
                label = section["label"]
                full_label = (
                    f"{prefix}.{label}" if prefix and label else label or prefix
                )
                labels.append(full_label)
                if section["subsections"]:
                    labels.extend(collect_labels(section["subsections"], full_label))
            return labels

        return collect_labels(self.body["subsections"])

    def get_text(
        self,
        subsection: str | None = None,
        indent: int = 2,
        headers: Literal["none", "normal", "verbose"] = "normal"
    ) -> str:
        def find_subsection(path: list[str], section: dict, parents: list[str]) -> tuple[dict | None, list[str]]:
            """Recursively find a subsection and return it along with its parent labels."""
            if not path:
                return section, parents
            for child in section.get("subsections", []):
                if child["label"] == path[0]:
                    return find_subsection(path[1:], child, parents + [child["label"]])
            return None, parents

        def format_section(section: dict, level: int = 0, parent_labels: list[str] | None = None) -> str:
            if parent_labels is None:
                parent_labels = []
            lines = []
            label = section["label"]

            if headers == "none":
                header_str = ""
            elif headers == "normal":
                header_str = f"{label}. " if label else ""
            elif headers == "verbose":
                full_label = ".".join(parent_labels) if parent_labels else ""
                header_str = f"{full_label}. " if full_label else ""

            text_line = f"{' ' * (level * indent)}{header_str}{section['text']}"
            lines.append(text_line)

            for child in section.get("subsections", []):
                child_labels = parent_labels + [child["label"]] if child["label"] else parent_labels
                lines.append(format_section(child, level + 1, child_labels))

            return "\n".join(lines)

        root = self.body
        if subsection:
            path = subsection.split(".")
            target, parents = find_subsection(path, root, [])
            if not target:
                return f"[Missing subsection: {subsection}]"
            return format_section(target, parent_labels=parents).strip()
        else:
            return format_section(root, parent_labels=[root["label"]] if root.get("label") else []).strip()


    def walk_subsections(self) -> Iterator[dict]:
        """Yield every section and subsection in the statute."""

        def recurse(sections):
            for section in sections:
                yield section
                yield from recurse(
                    section.get("subsections", [])
                )  # shamelessly stolen from SO

        yield from recurse(self.body)

    def contains_references(self) -> bool:
        """Ensure all or none of the sections include a 'references' field."""
        seen = []
        for sec in self.walk_subsections():
            has_ref = "references" in sec
            seen.append(has_ref)

        if not seen:
            return False  # no sections

        if all(seen):
            return True

        if not any(seen):
            return False

        raise ValueError("Mixed reference presence — corrupt statute data")

    def to_json(self) -> str:
        """Serialize the statute to a JSON string."""
        data = {
            "schema_version": self.SCHEMA_VERSION,
            "reference": self.reference.to_dict(),
            "name": self.name,
            "body": self.body,
            "history": self.history,
        }
        return json.dumps(data, indent=2)

    def to_file(self, folder_path: Path):
        """Write the statute to a JSON file in the given folder, using a generated name."""
        folder_path.mkdir(parents=True, exist_ok=True)

        # title = self.reference.get("title", "unknown")
        title = self.reference.title
        # section = self.reference.get("section", "unknown")
        section = self.reference.section
        # version = self.reference.get("version")
        version = self.reference.version

        filename_parts = [f"title_{title}", f"section_{section}"]
        if version:
            filename_parts.append(str(version))

        filename = "_".join(filename_parts) + ".json"
        path = folder_path / filename

        path.write_text(self.to_json(), encoding="utf-8")

    @staticmethod
    def from_json(json_input: Union[str, dict, Path]) -> "Statute":
        """Deserialize a Statute from JSON string, dict, or file path."""
        if isinstance(json_input, Path):
            json_str = json_input.read_text()
            data = json.loads(json_str)
        elif isinstance(json_input, str):
            data = json.loads(json_input)
        elif isinstance(json_input, dict):
            data = json_input
        else:
            raise TypeError("Unsupported input type for from_json")

        # Validate schema version
        if data.get("schema_version") != Statute.SCHEMA_VERSION:
            raise ValueError("Unsupported schema version")

        return Statute(
            reference=StatuteReference.from_dict(data["reference"]),
            name=data["name"],
            body=data["body"],
            history=data["history"],
        )
