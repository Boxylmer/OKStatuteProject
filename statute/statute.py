import json
from pathlib import Path
from typing import Iterator, Union


class Statute:
    """Main class that holds statute information."""

    SCHEMA_VERSION = 1  # In case you want versioning support

    def __init__(self, reference: dict, name: str, body: list, history):
        self.reference = reference  # {"title": title, "section": section, "version": version or None}

        self.name = name
        self.body = body
        # looks like this
        # [{'label': '', 'text': 'Baz', 'subsections': [{'label': 'A', 'text': 'Foo', 'subsections': []}, {'label': 'B', 'text': 'Bar', 'subsections': []}]}]
        # if contains references, looks like
        # [
        #   {'label': '', 'text': 'Baz', 'subsections': [
        #       {'label': 'A', 'text': 'Foo', 'subsections': [], 'references'=[]},
        #       {'label': 'B', 'text': 'Bar', 'subsections': [], 'references'=[]}
        #    ], 'references'=[]}
        # ]

        self.history = history

    def directory(self):
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

        return collect_labels(self.body)

    def get_text(self, subsection=None, indent=2):
        def format_section(section, parent_labels=[], level=0):
            label = section["label"] or None
            current_labels = parent_labels + [label] if label else parent_labels
            indent_space = " " * (level * indent)

            full_label = ".".join(filter(None, current_labels))
            display_label = f"{label}. " if label else ""

            if (
                subsection is None
                or full_label == subsection
                or (
                    subsection
                    and full_label
                    and full_label.startswith(subsection + ".")
                )
            ):
                lines = [f"{indent_space}{display_label}{section['text']}"]
                for sub in section["subsections"]:
                    lines.append(format_section(sub, current_labels, level + 1))
                return "\n".join(lines)
            return ""

        output = []
        for sec in self.body:
            result = format_section(sec)
            if result:
                output.append(result)

        return "\n".join(output).strip()

    def walk_subsections(self) -> Iterator[dict]:
        """Yield every section and subsection in the statute."""

        def recurse(sections):
            for section in sections:
                yield section
                yield from recurse(section.get("subsections", []))

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
            "title": self.reference,
            "name": self.name,
            "body": self.body,
            "history": self.history,
        }
        return json.dumps(data, indent=2)

    def to_file(self, folder_path: Path):
        """Write the statute to a JSON file in the given folder, using a generated name."""
        folder_path.mkdir(parents=True, exist_ok=True)

        title = self.reference.get("title", "unknown")
        section = self.reference.get("section", "unknown")
        version = self.reference.get("version")

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
            reference=data["title"],
            name=data["name"],
            body=data["body"],
            history=data["history"],
        )
