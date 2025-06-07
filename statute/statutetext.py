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

    def _extract_labeled_parts(self, line: str) -> list[tuple[str | None, str]]:
        """
        From a single line, extract a sequence of (label, content) pairs.
        e.g. 'B. (a) The word means ...' -> [('B', ''), ('a', 'The word means ...')]
        If no label is detected, return [(None, line)]
        """
        tokens: list[tuple[str | None, str]] = []
        remaining = line.strip()

        while remaining:
            matched = False
            for pattern, _ in self.SECTION_PATTERNS:
                match = re.match(pattern, remaining)
                if match:
                    raw_label = match.group()
                    label = self._clean_label(raw_label)
                    remaining = remaining[len(raw_label):].lstrip()
                    tokens.append((label, ""))  # We'll fill text later
                    matched = True
                    break

            if not matched:
                if tokens:
                    tokens[-1] = (tokens[-1][0], remaining)
                else:
                    tokens.append((None, remaining))
                break

        return tokens

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
            if not line:
                continue

            tokens = self._extract_labeled_parts(line)

            current_parent = None  # Will store the last added node (for chaining children)
            for label, text in tokens:
                if label is None:
                    node = {"label": None, "text": text, "subsections": []}
                    if current_parent:
                        current_parent["subsections"].append(node)
                    else:
                        root.append(node)
                    continue

                level = self._get_section_level(label + ".")

                node = {"label": label, "text": text, "subsections": []}

                # While stack is deeper or same level, pop it
                while stack and stack[-1][1] >= level:
                    stack.pop()

                # Push this as a child of stack top (or root)
                if stack:
                    stack[-1][0]["subsections"].append(node)
                else:
                    root.append(node)

                stack.append((node, level))
                current_parent = node  # so nested labels on same line chain down correctly

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

    def walk_sections(
        self, append_parents: bool = True, leaf_only: bool = False
    ) -> list[tuple[str, str]]:
        results = []

        def recurse(node, path_labels, path_texts, inherited_label=None):
            label = node.get("label")
            text = node.get("text", "")
            is_leaf = not node.get("subsections")

            if label is not None:
                new_path_labels = path_labels + [label]
                new_path_texts = path_texts + [text]
                name = ".".join(new_path_labels)
                full_text = ": ".join(new_path_texts) if append_parents else text

                if not leaf_only or is_leaf:
                    results.append((name, full_text))

                inherited_label = label  # Update most recent label
            else:
                if is_leaf:
                    inherited_name = ".".join(path_labels)
                    full_text = (
                        " ".join(path_texts + [text]) if append_parents else text
                    )
                    results.append((inherited_name, full_text))

            children = node.get("subsections", [])
            for child in children:
                recurse(
                    child,
                    path_labels if label is None else new_path_labels,
                    path_texts if label is None else new_path_texts,
                    inherited_label,
                )

        for root in self.structured_data:
            recurse(root, [], [], None)

        return results
