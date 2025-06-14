# import re
# from typing import List, Optional, Tuple
# from enum import StrEnum
# from statute.statutenode import StatuteNode

# class LabelType(StrEnum):
#     UPPER = "upper"
#     NUMBER = "number"
#     LOWER = "lower"
#     PAREN_UPPER = "paren_upper"
#     PAREN_NUMBER = "paren_number"
#     PAREN_LOWER = "paren_lower"
#     ROMAN = "roman"

# class StatuteTree:
#     LABEL_ORDER = list(LabelType)
#     LABEL_ORDER_INDEX = {label: i for i, label in enumerate(LABEL_ORDER)}

#     LABEL_PATTERNS: List[Tuple[str, LabelType]] = [
#         (r"^[A-Z]\.$", LabelType.UPPER),
#         (r"^\d+\.$", LabelType.NUMBER),
#         (r"^[a-z]\.$", LabelType.LOWER),
#         (r"^\([A-Z]\)$", LabelType.PAREN_UPPER),
#         (r"^\(\d+\)$", LabelType.PAREN_NUMBER),
#         (r"^\([a-z]\)$", LabelType.PAREN_LOWER),
#         (r"^i{1,3}$|^iv$|^v$|^vi{0,3}$|^ix$|^x$", LabelType.ROMAN),
#     ]

#     def __init__(self, lines: List[str]):
#         self.lines = lines
#         self.root = StatuteNode(text="Root")
#         self.build()
#         print(self.root.subsections)

#     def build(self):
#         stack = [(0, self.root)]
#         for line in self.lines:
#             parts = self._split_line_by_labels(line)
#             for label, text in parts:
#                 self._add_node(label, text, stack)

#     def _normalize_label(self, label: str) -> str:
#         return label.strip("().")

#     def _split_line_by_labels(self, line: str) -> List[Tuple[Optional[str], str]]:
#         pattern = r"((?:[A-Z]\.|[a-z]\.|\d+\.|\([A-Z]\)|\([a-z]\)|\(\d+\)))"
#         tokens = re.split(pattern, line)
#         results: List[Tuple[Optional[str], str]] = []
#         current_label: Optional[str] = None
#         buffer = ""

#         for token in tokens:
#             if not token.strip():
#                 continue
#             if re.match(pattern, token):
#                 if buffer:
#                     results.append((current_label, buffer.strip()))
#                     buffer = ""
#                 current_label = token
#             else:
#                 buffer += " " + token

#         if buffer:
#             results.append((current_label, buffer.strip()))

#         return results

#     def _add_node(self, label: Optional[str], text: str, stack: List[Tuple[int, StatuteNode]]):
#         print("Label node: ", label)
#         print("Label text: ", text)
#         print("Label stack: ", stack)
#         normalized_label = self._normalize_label(label) if label else None
#         node = StatuteNode(text=text.strip(), label=normalized_label)

#         if not label:
#             stack[-1][1].text += " " + text.strip()
#             return

#         label_type = self._get_label_type(label)
#         if label_type is None:
#             stack[-1][1].add_subsection(node)
#             return

#         while len(stack) > 1:
#             parent_label = stack[-1][1].label
#             parent_type = self._get_label_type(parent_label)
#             if self._is_child_label(label_type, parent_type):
#                 break

#             stack.pop()

#         stack[-1][1].add_subsection(node)
#         stack.append((len(stack), node))

#     @classmethod
#     def _get_label_type(cls, label: Optional[str]) -> Optional[str]:
#         if not label:
#             return None
#         for pattern, label_type in cls.LABEL_PATTERNS:
#             if re.match(pattern, label):
#                 return label_type.value
#         return None

#     @classmethod
#     def _is_child_label(cls, current_type: Optional[str], parent_type: Optional[str]) -> bool:
#         if current_type is None or parent_type is None:
#             return False
#         return cls.LABEL_ORDER_INDEX[current_type] > cls.LABEL_ORDER_INDEX[parent_type]

#     def as_dict(self):
#         return self.root.as_dict()

#     def walk(self, **kwargs):
#         return self.root.walk(**kwargs)
import re
from typing import List, Tuple, Optional
from statute.statutenode import StatuteNode


class LabelType:
    UPPER = "UPPER"
    NUMBER = "NUMBER"
    LOWER = "LOWER"
    PAREN_UPPER = "PAREN_UPPER"
    PAREN_NUMBER = "PAREN_NUMBER"
    PAREN_LOWER = "PAREN_LOWER"
    ROMAN = "ROMAN"  # optional


class StatuteTree:
    LABEL_PATTERNS = [
        (r"^[A-Z]\.$", LabelType.UPPER),
        (r"^\d+\.$", LabelType.NUMBER),
        (r"^[a-z]\.$", LabelType.LOWER),
        (r"^\([A-Z]\)$", LabelType.PAREN_UPPER),
        (r"^\(\d+\)$", LabelType.PAREN_NUMBER),
        (r"^\([a-z]\)$", LabelType.PAREN_LOWER),
        (r"^i{1,3}$|^iv$|^v$|^vi{0,3}$|^ix$|^x$", LabelType.ROMAN),
    ]

    LABEL_ORDER = [
        LabelType.UPPER,
        LabelType.NUMBER,
        LabelType.LOWER,
        LabelType.ROMAN,
    ]
    LABEL_ORDER_INDEX = {label: i for i, label in enumerate(LABEL_ORDER)}

    def __init__(self, lines: List[str]):
        self.lines = lines
        self.root = StatuteNode(text="Root")
        self.build()

    def _normalize_label(self, label: str) -> str:
        return label.strip("().")

    def _get_label_type(self, label: str) -> Optional[str]:
        for pattern, label_type in self.LABEL_PATTERNS:
            if re.fullmatch(pattern, label):
                return label_type
        return None

    def _is_child_label(self, child_type: str, parent_type: str) -> bool:
        return self.LABEL_ORDER_INDEX.get(child_type, -1) > self.LABEL_ORDER_INDEX.get(parent_type, -1)

    def build(self):
        stack: List[Tuple[int, StatuteNode]] = [(0, self.root)]

        for line in self.lines:
            line = line.strip()
            if not line:
                continue

            labels = []
            rest = line

            while True:
                match = re.match(r"^(\(?[A-Za-z0-9]+\)?\.?)\s+", rest)
                if not match:
                    break
                label = match.group(1)
                labels.append(label)
                rest = rest[match.end():]

            if not labels:
                # continuation line
                stack[-1][1].text += " " + rest.strip()
                continue

            # insert nodes for each label
            for i, label in enumerate(labels):
                norm_label = self._normalize_label(label)
                label_type = self._get_label_type(label)
                node = StatuteNode(text="", label=norm_label)

                # walk back up until we find a valid parent
                while len(stack) > 1:
                    parent_label = stack[-1][1].label
                    parent_type = self._get_label_type(parent_label)
                    if label_type and self._is_child_label(label_type, parent_type):
                        break
                    stack.pop()

                # check for duplicates at this level
                existing = [n.label for n in stack[-1][1].subsections]
                if norm_label not in existing:
                    stack[-1][1].add_subsection(node)
                    stack.append((len(stack), node))
                else:
                    # if already exists, just push it onto the stack
                    for sub in stack[-1][1].subsections:
                        if sub.label == norm_label:
                            stack.append((len(stack), sub))
                            break

            # assign text to last label node
            stack[-1][1].text += " " + rest.strip()

    def walk(
        self,
        node: Optional[StatuteNode] = None,
        path: Optional[List[str]] = None,
        text_path: Optional[List[str]] = None,
        append_parents: bool = False,
        leaf_only: bool = False
    ) -> List[Tuple[str, str]]:
        if node is None:
            node = self.root
        if path is None:
            path = []
        if text_path is None:
            text_path = []

        results = []
        is_root = (node == self.root)

        # skip root from path
        if node.label:
            path = path + [node.label]
        if node.text and node.label:
            text_path = text_path + [node.text.strip()]

        is_leaf = not node.subsections

        if (not leaf_only or is_leaf) and not is_root:
            label_str = ".".join(path)
            text_str = ": ".join(text_path) if append_parents else node.text.strip()
            results.append((label_str, text_str))

        for child in node.subsections:
            results.extend(self.walk(child, path, text_path, append_parents, leaf_only))

        return results