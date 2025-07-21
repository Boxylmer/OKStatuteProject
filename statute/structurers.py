import re
from re import Pattern
from typing import List, Dict, Tuple, Any, Optional


class StatuteBodyStructurer:
    """
    Break a statute body into a structured format.

    Detection finds the first of the MARKER_PATTERNS and holds on to it for that "level"
    I have no idea if the other staute titles follow this format,
        if you use something other than title 21 and it breaks, I'm sorry.
        We definitely need a ton of unittests on this thing.

    Level Header Pattern Order:
        1. Capital Letters: A., B., C., ...
        2. Numbers: 1., 2., 3., ...
        3. Lowercase Letters: a., b., c., ...
        # TODO maybe we will need i, ii, ...? This is harder and I didn't want to waste time on it yet.
    """

    MARKER_PATTERNS = [
        (r"^\s*([A-Z])\. ", "alpha_upper"),  # A. B. C.
        (r"^\s*(\d+)\. ", "numeric"),  # 1. 2. 3.
        (r"^\s*([a-z])\. ", "alpha_lower"),  # a. b. c.
    ]

    def __init__(self):
        self._structure = []
        self.stack = []
        self.level_order = []
        self.pending_root_level = False

    def structure(
        self, raw_body_text: str, check_consistency=True
    ) -> List[Dict[str, Any]]:
        cleaned_text = self._remove_soft_newlines(raw_body_text)
        lines = cleaned_text.strip().splitlines()

        for line in lines:
            self._process_line(line)

        # Modify structure with an unlabeled toplevel section and multiple labeled toplevel sections to be nested instead
        if len(self._structure) > 1 and self._structure[0]["label"] == "":
            unlabeled_intro = self._structure[0]
            the_rest = self._structure[1:]

            # Check that all the rest are labeled and that labels form a consistent sequence
            all_labeled = all(s.get("label") for s in the_rest)

            if all_labeled:
                unlabeled_intro["subsections"].extend(the_rest)
                self._structure = [unlabeled_intro]

        if check_consistency:
            self._check_consistency(self._structure)

        return self._structure

    def _check_line_for_label(self, line: str) -> tuple[str, str, int] | None:
        """
        Returns (label, label_type, match_end) if a label is found at start of line, else None.
        """
        for pattern, label_type in self.MARKER_PATTERNS:
            match = re.match(pattern, line)
            if match:
                label = match.group(1).replace(".", "")
                return label, label_type, match.end()
        return None

    @staticmethod
    def _get_other_type_starters(label_type: str) -> Pattern:
        """
        Given a label_type ('numeric', 'alpha_upper', or 'alpha_lower'),
        return regex patterns to detect starter inline labels for the other two types.
        These can appear anywhere in the line as long as they are preceded by whitespace or start-of-line.

        Returns:
            Regex pattern
        """
        starter_literals = {
            "alpha_upper": "A",
            "alpha_lower": "a",
            "numeric": "1",
        }

        other_types = [lt for lt in starter_literals if lt != label_type]

        patterns = []
        for lt in other_types:
            literal = re.escape(starter_literals[lt] + ". ")
            # Match either start of line or whitespace before the literal
            pattern = rf"(?:(?<=^)|(?<=\s)){literal}"
            patterns.append(pattern)

        combined_pattern = "|".join(patterns)
        return re.compile(combined_pattern)

    def _process_line(self, line: str):
        match = self._check_line_for_label(line)
        if not match:
            self._append_to_last(line)
            return

        label, label_type, match_end = match
        if label_type not in self.level_order:
            self.level_order.append(label_type)

        content = line[match_end:].strip()

        # If content starts with another label, recursively split
        if self._check_line_for_label(content):
            self._push_section(label, label_type, "")
            self._process_line(content)
            return

        # if content contains an expected inline label, recursively split
        inline_pattern = self._get_other_type_starters(label_type)
        inline_match = inline_pattern.search(content)

        if inline_match:
            split_idx = inline_match.start()
            before = content[:split_idx].strip()
            after = content[split_idx:].strip()

            self._push_section(label, label_type, before)
            self._process_line(after)
            return

        # all other edge cases not happening: just add it to the section
        self._push_section(label, label_type, content)

    def _extract_label(self, line: str) -> tuple[str, str, str]:
        match = self._check_line_for_label(line)
        if match:
            label, label_type, match_end = match
            if label_type not in self.level_order:
                self.level_order.append(label_type)
            return label, label_type, line[match_end:].strip()
        return "", "", line.strip()

    def _push_section(self, label: str, label_type: str, content: str):
        level = self.level_order.index(label_type)
        section = {"label": label, "text": content, "subsections": []}

        while len(self.stack) > level:
            self.stack.pop()

        if not self.stack:
            self._structure.append(section)
        else:
            self.stack[-1]["subsections"].append(section)

        self.stack.append(section)

    def _append_to_last(self, line: str):
        if self.stack:
            self.stack[-1]["text"] += " " + line.strip()
        elif self._structure:
            self._structure[-1]["text"] += " " + line.strip()
        else:
            self._structure.append(
                {"label": "", "text": line.strip(), "subsections": []}
            )

    def _check_consistency(self, sections: List[Dict[str, Any]]):
        "Did I actually get something in the right order? I.e., A->B->1->2->C->1->2..."
        for level_sections in [sections]:
            self._check_recursive(level_sections)

    def _check_recursive(self, sections: List[Dict[str, Any]]):
        labels = [s["label"] for s in sections if s["label"]]
        if not labels:
            return

        # Check for numeric sequence: 1, 2, 3, ...
        if all(label.isdigit() for label in labels):
            nums = list(map(int, labels))
            expected = list(range(1, len(nums) + 1))
            if nums != expected:
                raise ValueError(
                    f"Inconsistent numeric label sequence: expected {expected}, got {nums}."
                )

        # Check for alphabetic sequence: A, B, C, ... or a, b, c, ...
        elif all(len(label) == 1 and label.isalpha() for label in labels):
            ords = [ord(label.lower()) for label in labels]
            expected = list(range(ord("a"), ord("a") + len(ords)))
            if ords != expected:
                raise ValueError(
                    f"Inconsistent alphabetic label sequence: expected {[chr(o).upper() for o in expected]}, got {labels}"
                )

        # Recurse into nested sections
        for section in sections:
            self._check_recursive(section["subsections"])

    def _remove_soft_newlines(self, text: str) -> str:
        lines = text.splitlines()
        cleaned = []
        buffer = ""

        for i in range(len(lines)):
            current = buffer if buffer else lines[i]
            current = current.rstrip()
            if not current:
                continue
            if i + 1 >= len(lines):
                cleaned.append(current)
                break

            next_line = lines[i + 1]
            stripped_next = next_line.strip()

            # Rule 1: current ends in alphanumeric or comma
            ends_in_soft_char = current[-1].isalnum() or current[-1] == ","

            # Rule 2: next line is not indented (i.e., doesn't start with whitespace)
            starts_without_indent = not next_line[:1].isspace()

            if ends_in_soft_char and starts_without_indent:
                # Merge with next line
                buffer = current + " " + stripped_next
                lines[i + 1] = ""  # Consume next line
            else:
                cleaned.append(current)
                buffer = ""

        return "\n".join(cleaned)


class StatuteReferenceStructurer:
    def __init__(self):
        pass

    def structure(self, raw_ref_text) -> dict:
        """
        Parses a statute title like '§21-54.1v2' into:
            - title: '21'
            - section: '54.1'
            - version: '2' (or None)
        Returns:
            [title (str), section (str), version (str or None)]
        """

        # Remove § symbol and trailing punctuation
        text = raw_ref_text.strip().lstrip("§").rstrip(".: ")

        # Match patterns like 21-54.1v2 or 21-123a
        match = re.match(r"(\d+)-([A-Za-z0-9.-]+?)(?:v(\d+))?$", text)
        if not match:
            raise ValueError(f"Unrecognized title format: {raw_ref_text}")

        title, section, version = match.groups()
        return {"title": title, "section": section, "version": version or None}
        # return [title, section, version or None]
