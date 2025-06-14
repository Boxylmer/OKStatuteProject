from typing import List, Optional


class StatuteNode:
    def __init__(
        self,
        text: str,
        label: Optional[str] = None,
        subsections: Optional[List["StatuteNode"]] = None,
    ):
        self.label = label  # like "A", "1", or None
        self.text = text.strip()
        self.subsections = subsections if subsections is not None else []

    def add_subsection(self, node: "StatuteNode") -> None:
        self.subsections.append(node)

    def is_leaf(self) -> bool:
        return not self.subsections

    def full_label(self, parent_labels: Optional[List[str]] = None) -> str:
        parent_labels = parent_labels or []
        return (
            ".".join(parent_labels + [self.label])
            if self.label
            else ".".join(parent_labels)
        )

    def walk(
        self,
        append_parents: bool = True,
        leaf_only: bool = False,
        parent_labels: Optional[List[str]] = None,
        parent_texts: Optional[List[str]] = None,
    ) -> List[tuple[str, str]]:
        parent_labels = parent_labels or []
        parent_texts = parent_texts or []

        results = []

        current_labels = parent_labels + ([self.label] if self.label else [])
        current_texts = parent_texts + [self.text]

        name = ".".join(current_labels)
        full_text = ": ".join(current_texts) if append_parents else self.text

        if not leaf_only or self.is_leaf():
            results.append((name, full_text))

        for subsection in self.subsections:
            results.extend(
                subsection.walk(
                    append_parents, leaf_only, current_labels, current_texts
                )
            )

        return results

    def as_dict(self) -> dict:
        return {
            "text": self.text,
            "label": self.label,
            "subsections": [s.as_dict() for s in self.subsections],
        }

    @staticmethod
    def from_dict(data: dict) -> "StatuteNode":
        return StatuteNode(
            text=data.get("text", ""),
            label=data.get("label"),
            subsections=[StatuteNode.from_dict(d) for d in data.get("subsections", [])],
        )
