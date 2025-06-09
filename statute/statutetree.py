import re
from collections import deque
from statute.statutenode import StatuteNode

LABEL_PATTERNS = [
    (r"^[A-Z]\.", "upper"),  # A.
    (r"^\d+\.", "number"),  # 1.
    (r"^[a-z]\.", "lower"),  # a.
    (r"^\([A-Z]\)", "paren_upper"),  # (A)
    (r"^\([0-9]+\)", "paren_number"),  # (1)
    (r"^\([a-z]\)", "paren_lower"),  # (a)
    (
        r"^(First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth)\.",
        "ordinal",
    ),
]


def match_label(text):
    for pattern, label_type in LABEL_PATTERNS:
        match = re.match(pattern, text)
        if match:
            return match.group(), label_type
    return None, None


def clean_label(label):
    return re.sub(r"[().]", "", label).strip()


class StatuteTree:
    def __init__(self, lines: list[str]):
        self.root_nodes = self._parse_lines(lines)

    def _parse_lines(self, lines: list[str]) -> list[StatuteNode]:
        stack: deque[tuple[StatuteNode, str]] = deque()
        roots: list[StatuteNode] = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            segments = self._split_line_into_labeled_segments(line)
            for raw_label, label_type, text in segments:
                label = clean_label(raw_label) if raw_label else None
                node = StatuteNode(text=text, label=label)

                if not label:
                    if stack:
                        stack[-1][0].add_subsection(node)
                    else:
                        roots.append(node)
                    continue

                while stack and not self._is_child_label(label_type, stack[-1][1]):
                    stack.pop()

                if stack:
                    stack[-1][0].add_subsection(node)
                else:
                    roots.append(node)

                stack.append((node, label_type))

        return roots

    def _split_line_into_labeled_segments(
        self, line: str
    ) -> list[tuple[str | None, str | None, str]]:
        """
        Splits a line into segments like:
        "B. (a) The dog is friendly." -> [("B.", "upper", ""), ("(a)", "paren_lower", "The dog is friendly.")]
        """
        parts = []
        remaining = line
        while remaining:
            raw_label, label_type = match_label(remaining)
            if raw_label:
                content_start = remaining[len(raw_label) :].lstrip()
                parts.append((raw_label, label_type, content_start))
                remaining = content_start
            else:
                if parts:
                    last = parts.pop()
                    parts.append((last[0], last[1], last[2] + " " + remaining))
                else:
                    parts.append((None, None, remaining))
                break
        return parts

    def _is_child_label(self, current_type: str, parent_type: str) -> bool:
        order = [
            "upper",
            "number",
            "lower",
            "paren_upper",
            "paren_number",
            "paren_lower",
            "ordinal",
        ]
        try:
            return order.index(current_type) > order.index(parent_type)
        except ValueError:
            return False

    def as_dict(self) -> list[dict]:
        return [node.as_dict() for node in self.root_nodes]

    def walk(self, **kwargs):
        all_walks = []
        for node in self.root_nodes:
            all_walks.extend(node.walk(**kwargs))
        return all_walks
