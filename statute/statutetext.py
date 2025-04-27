from collections import deque
import json
import re
from typing import Any


class StatuteText:
    SECTION_PATTERNS = [
        (r"^[A-Z]\.", 1),  # A., B., C.
        (r"^\d+\.", 2),  # 1., 2., 3.
        (r"^[a-z]\.", 3),  # a., b., c.
        (r"^\([A-Z]\)", 4),  # (A), (B)
        (r"^\([0-9]+\)", 5),  # (1), (2)
        (r"^\([a-z]\)", 7),  # (a), (b), (c)
        (
            r"^(First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth)\.",
            6,
        ),  # Ordinal
    ]

    def __init__(self, raw_texts: list[str]):
        """
        Parse the lines of text from the statute as a hierarchy of data from its labeling.
        """
        self.structured_data = self._parse(raw_texts)

    def _get_section_level(self, text: str) -> int:
        for pattern, level in self.SECTION_PATTERNS:
            if re.match(pattern, text.strip()):
                return level
        return 0

    def _clean_label(self, label: str) -> str:
        return re.sub(r"[().]", "", label).rstrip(".")

    def _parse(self, raw_texts) -> list[dict]:
        root = []
        stack: deque[tuple[Any, int]] = deque()

        for line in raw_texts:
            line = line.strip()
            level = self._get_section_level(line)

            if level == 0:
                node = {"label": None, "text": line, "subsections": []}
                root.append(node)
                continue

            seen_structure = True
            node = {"text": line, "subsections": []}
            label_match = re.match(r"^([\w\(\)\.]+)\s+(.*)", line)

            if label_match:
                raw_label, content = label_match.groups()
                node["label"] = self._clean_label(raw_label)
                node["text"] = content
            else:
                node["label"] = None

            while stack and stack[-1][1] >= level:
                stack.pop()

            if stack:
                stack[-1][0]["subsections"].append(node)
            else:
                root.append(node)

            stack.append((node, level))

        return root

    def as_list(self) -> list[dict]:
        return self.structured_data

    def as_json(self) -> str:
        return json.dumps(self.structured_data, indent=2)

    def as_text(
        self, subsection: str = "", pretty: bool = False, indent: int = 2
    ) -> str:
        nodes = (
            self.structured_data
            if not subsection
            else [self._get_subsection(subsection)]
        )
        if not nodes or nodes[0] is None:
            return ""

        def render(node, level=0):
            label = node.get("label")
            text = node.get("text", "")
            prefix = f"{label}. " if label else ""
            line = f"{prefix}{text}".strip()

            if pretty:
                pad = " " * (indent * level)
                lines = [f"{pad}{line}"]
                for child in node.get("subsections", []):
                    lines.append(render(child, level + 1))
                return "\n".join(lines)
            else:
                lines = [line]
                for child in node.get("subsections", []):
                    lines.append(render(child, level + 1))
                return " ".join(lines)

        rendered = [render(node) for node in nodes]
        return "\n\n".join(rendered) if pretty else " ".join(rendered)

    @staticmethod
    def from_json(json_str: str) -> "StatuteText":
        data = json.loads(json_str)
        instance = StatuteText([])
        instance.structured_data = data
        return instance

    def subsection_names(self) -> list[str]:
        results = []

        def walk(nodes, path=[]):
            for node in nodes:
                label = node.get("label")
                new_path = path + [label] if label else path
                if label:
                    results.append(".".join(new_path))
                walk(node.get("subsections", []), new_path)

        walk(self.structured_data)
        return results

    def _get_subsection(self, subsection_name: str) -> dict:
        target = subsection_name.split(".")

        def find(nodes, path):
            for node in nodes:
                if node.get("label") == path[0]:
                    if len(path) == 1:
                        return node
                    return find(node.get("subsections", []), path[1:])
            return {}

        return find(self.structured_data, target)
