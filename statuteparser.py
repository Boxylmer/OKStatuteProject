import hashlib
import json
from pathlib import Path
import re
from re import Pattern
from typing import List, Dict, Tuple, Any, Optional
import pymupdf4llm  # type: ignore


def match_string_prefix_fuzzy(body: str, prefix: str) -> int | None:
    """
    Find the line-up index of a prefix in a body of text, ignoring whitespace, newlines, etc.
    The index returned is the ending position of the prefix string for the *body* text.
    E.g.,
    Body: " The
            quick brow
            n fox jumped over the lazy dog"
    Target: "the quick brown
    Result: 15

    """
    b_idx = 0
    p_idx = 0

    def normalize(c):
        return c.lower() if c.isalnum() else None

    while b_idx < len(body) and p_idx < len(prefix):
        # Skip whitespace in body
        if body[b_idx].isspace():
            b_idx += 1
            continue

        # Skip whitespace in prefix
        if prefix[p_idx].isspace():
            p_idx += 1
            continue

        # Skip non-alphanumerics in both
        b_char = normalize(body[b_idx])
        while b_char is None and b_idx < len(body):
            b_idx += 1
            if b_idx < len(body):
                b_char = normalize(body[b_idx])

        p_char = normalize(prefix[p_idx])
        while p_char is None and p_idx < len(prefix):
            p_idx += 1
            if p_idx < len(prefix):
                p_char = normalize(prefix[p_idx])

        # If either index is now out of range, break
        if p_idx >= len(prefix):
            break
        if b_idx >= len(body):
            break

        # Compare normalized characters
        if b_char != p_char:
            return None

        # Advance
        b_idx += 1
        p_idx += 1

    # Confirm full prefix consumed
    while p_idx < len(prefix):
        if normalize(prefix[p_idx]) is not None:
            return None
        p_idx += 1

    return b_idx  # prefix / body had total line-up, # TODO maybe another error or just return an empty string? Not sure yet.

    # TODO: Not sure what I should be doing to make this more readable. Kind of bog standard fuzzy string matching logic, but very much not pythonic.


class StatuteParser:
    STATUTE_HEADER_RE = re.compile(r"^§[^\s]+-[^\s]+\.", re.MULTILINE)
    HISTORICAL_DATA_STARTERS = (
        "Added by Laws",
        "Amended by Laws",
        "Added by State Question",
        # "Renumbered as",
        # "Repealed by Laws",
        "Laws ",
        "R.L.",
    )

    def __init__(self, pdf_path: Path, cache_dir: Path = Path("cache")):
        self.pdf_path = Path(pdf_path)
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.md5_hash = self._compute_md5()
        self.raw_markdown_path = self.cache_dir / f"raw_{self.md5_hash}.md"
        self.cleaned_json_path = self.cache_dir / f"split_{self.md5_hash}.json"

    def parse(self):
        clean_statute_info = self._parse_statute_pdf_text()

        return clean_statute_info

    def _compute_md5(self) -> str:
        hasher = hashlib.md5()
        with open(self.pdf_path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _parse_pdf_to_text(self) -> str:
        if self.raw_markdown_path.exists():
            return self.raw_markdown_path.read_text(encoding="utf-8")
        text = pymupdf4llm.to_markdown(str(self.pdf_path), use_glyphs=True)
        self.raw_markdown_path.write_text(text, encoding="utf-8")
        return text

    @staticmethod
    def _extract_first_statute_name(raw_text: str) -> str:
        """
        Parses the TOC text and returns the first statute header (e.g., '§21-1.')
        """
        STATUTE_HEADER_RE = re.compile(r"(§[^\s]+-[^\s]+\.)")
        for line in raw_text.splitlines():
            match = STATUTE_HEADER_RE.search(line)
            if match:
                return match.group(1)
        raise ValueError("Could not find a statute header in the TOC.")

    @staticmethod
    def _split_raw_pdf_text_into_components(raw_pdf_text: str):
        break_point = StatuteParser._extract_first_statute_name(raw_pdf_text)
        parts = raw_pdf_text.split(break_point)
        assert len(parts) == 3, "Unable to split into header, TOC, contents."
        header, toc, contents = parts
        # Add the breaking character back to the toc and contents.
        toc = break_point + toc
        contents = break_point + contents
        return header, toc, contents

    @staticmethod
    def _clean_statute_text_pages(markdown_text: str) -> str:
        "Take the raw pages from the PDF and strip out formatting + extraneous information like headers and footers."
        cleaned_lines = []
        footer_pattern = re.compile(r"^Oklahoma Statutes - Title \d+\. .* Page \d+$")
        for line in markdown_text.splitlines():
            if footer_pattern.match(line.strip()):
                continue
            if line.strip() == "```":
                continue
            cleaned_lines.append(line)
        return "\n".join(cleaned_lines)

    @staticmethod
    def _split_title_from_statute_data(
        clean_statute_text: str,
    ) -> List[Tuple[str, str]]:
        """
        Given a clean text with statute information, split the text by the start of each statute occurance and extract a title and body for each.
        returns: list[(title, raw_body), ...]
        """

        matches = list(StatuteParser.STATUTE_HEADER_RE.finditer(clean_statute_text))
        statutes = []

        for i, match in enumerate(matches):
            start = match.start()
            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(clean_statute_text)
            )
            title = match.group().strip()
            raw_statute = clean_statute_text[start:end].strip()
            statutes.append((title, raw_statute))
        return statutes

    @staticmethod
    def _clean_toc_name(raw_toc_text: str, title_text: str):
        "Remove ellipses, title, and page numbers from the TOC entry."
        # Forcefully collapse newlines and multiple spaces
        toc_entry = re.sub(r"\s+", " ", raw_toc_text).strip()

        # Mercilessly remove trailing dots + optional page number
        toc_entry = re.sub(r"\.{2,}\s*\d+\s*$", "", toc_entry).strip()

        # Destroy, inhumanely, the title text
        if not toc_entry.startswith(title_text):
            raise ValueError(
                f"Statute number '{title_text}' not found at start of '{toc_entry}'"
            )

        toc_entry = toc_entry[len(title_text) :].strip()
        return toc_entry

    @staticmethod
    def _clean_statute_body(
        raw_statute_body: str, statute_name: str, statute_title: str
    ) -> tuple[str, str]:
        "Remove the name and title from the statute body and split the body into the contents and historical data."

        if statute_name.lower().strip().startswith("repealed"):
            return "repealed", raw_statute_body

        if statute_name.lower().strip().startswith("renumbered"):
            return "renumbered", raw_statute_body

        # Remove title
        if not raw_statute_body.startswith(statute_title):
            raise ValueError(
                f"Statute number '{statute_title}' not found at start of '{raw_statute_body}'"
            )
        statute_body = raw_statute_body[len(statute_title) :].strip()

        match_end = match_string_prefix_fuzzy(body=statute_body, prefix=statute_name)
        if match_end is None:
            raise ValueError(
                f"Statute name '{statute_name}' not found at start of statute body (fuzzy match).\n'{statute_body}'"
            )

        statute_body = statute_body[match_end:].lstrip()

        historical_pattern = re.compile(
            r"(?m)^[ \t]*("
            + "|".join(re.escape(s) for s in StatuteParser.HISTORICAL_DATA_STARTERS)
            + r")"
        )

        match = historical_pattern.search(statute_body)
        if match:
            split_index = match.start()
            historical_data = statute_body[split_index:].lstrip()
            statute_body = statute_body[:split_index].rstrip()
        else:
            statute_body = statute_body
            historical_data = ""

        return statute_body, historical_data

    def _parse_statute_pdf_text(self) -> list[tuple[str, str, str, str]]:
        """
        Get the raw statute pdf text and segment out the text, title, and name of each statute.
        Verifies that all statutes have been found via the table of contents (TOC).

        Returns: [(statute_title, statute_name, statute_body, statute_history), ...]
        """

        md_text = self._parse_pdf_to_text()

        _, raw_toc, raw_statute_contents = self._split_raw_pdf_text_into_components(
            md_text
        )

        contents_cleaned = self._clean_statute_text_pages(raw_statute_contents)
        statute_chunks = self._split_title_from_statute_data(contents_cleaned)
        raw_statute_bodies = [chunk[1] for chunk in statute_chunks]

        self.cleaned_json_path.write_text(
            json.dumps(raw_statute_bodies, indent=2), encoding="utf-8"
        )

        # Consistency check: TOC headers match actual headers
        toc_cleaned = self._clean_statute_text_pages(raw_toc)
        toc_headers = [h for h in self._split_title_from_statute_data(toc_cleaned)]
        toc_titles = [h[0] for h in toc_headers]
        toc_names = [h[1] for h in toc_headers]
        content_headers = [h[0] for h in statute_chunks]
        missing = [h for h in toc_titles if h not in content_headers]
        if missing:
            print(f"⚠️ Warning: {len(missing)} TOC headers not found in parsed content.")
            for m in missing[:5]:
                print(f"  Missing: {m}")
            raise ValueError("Statute had missing content")

        clean_names = [
            self._clean_toc_name(name, title)
            for name, title in zip(toc_names, toc_titles)
        ]

        clean_statute_bodies_and_history = [
            self._clean_statute_body(raw_body, name, title)
            for raw_body, name, title in zip(
                raw_statute_bodies, clean_names, toc_titles
            )
        ]

        unstructured_clean_bodies = [
            body for body, _ in clean_statute_bodies_and_history
        ]
        clean_historical_data = [
            history for _, history in clean_statute_bodies_and_history
        ]

        unstructured_clean_bodies, clean_historical_data
        # formatted_titles = [self._format_title(title) for title in toc_titles]
        return list(
            zip(
                toc_titles,
                clean_names,
                unstructured_clean_bodies,
                clean_historical_data,
            )
        )


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

    INLINE_MARKER_PATTERNS = [
        (r"(?:^|\s)([A-Z])\. ", "alpha_upper"),  # A.
        (r"(?:^|\s)(\d+)\. ", "numeric"),  # 1.
        (r"(?:^|\s)([a-z])\. ", "alpha_lower"),  # a.
    ]

    PERMITTED_NESTING = {
        "alpha_upper": [
            "alpha_upper",
            "numeric",
            "alpha_lower",
        ],  # A. followed by B., 1., a.
        "numeric": ["numeric", "alpha_lower"],  # 1. followed by 2., a.
        "alpha_lower": ["alpha_lower", "numeric"],  # a. followed by b., 1.
    }

    def __init__(self):
        self._structure = []
        self.stack = []
        self.level_order = []

    def structure(
        self, raw_body_text: str, check_consistency=True
    ) -> List[Dict[str, Any]]:
        cleaned_text = self._remove_soft_newlines(raw_body_text)
        lines = cleaned_text.strip().splitlines()


        for line in lines:
            self._process_line(line)
        
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
    def get_other_type_starters(label_type: str) -> Pattern:
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
        inline_pattern = self.get_other_type_starters(label_type)
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

class StatuteTitleStructurer:
    def __init__(self):
        pass

    def structure(self, raw_title_text):
        """
        Parses a statute title like '§21-54.1v2' into:
            - title: '21'
            - section: '54.1'
            - version: '2' (or None)
        Returns:
            [title (str), section (str), version (str or None)]
        """

        # Remove § symbol and trailing punctuation
        text = raw_title_text.strip().lstrip("§").rstrip(".: ")

        # Match patterns like 21-54.1v2 or 21-123a
        match = re.match(r"(\d+)-([A-Za-z0-9.-]+?)(?:v(\d+))?$", text)
        if not match:
            raise ValueError(f"Unrecognized title format: {raw_title_text}")

        title, section, version = match.groups()
        return [title, section, version or None]



# put in own file
class Statute:
    """Main class that holds statute information."""

    def __init__(self, title: list, name: str, body: list, history, references=None):
        self.title = title
        self.name = name
        self.body = body
        self.history = history
        self.references = references

    def directory(self):
        def collect_labels(sections, prefix=""):
            labels = []
            for section in sections:
                label = section["label"]
                if not label: 
                    continue
                full_label = f"{prefix}.{label}" if prefix and label else label or prefix
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

            # Construct full label and local label
            full_label = ".".join(filter(None, current_labels))
            display_label = f"{label}. " if label else ""

            # Decide whether to include this section
            if subsection is None or full_label == subsection or (
                subsection and full_label and subsection.startswith(subsection + ".")
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

def test_statute_title_structurer():
    ans = StatuteTitleStructurer().structure("§21-54.1v2")
    assert ans == ['21', '54.1', '2']

    ans = StatuteTitleStructurer().structure("§21-123a.")
    assert ans == ['21', '123a', None]

    ans = StatuteTitleStructurer().structure("§63-312.5:")
    assert ans == ['63', '312.5', None]


# Too lazy to structure this as a real package right now so am putting test functions here to eventually become unit tests
def test_match_string_prefix_fuzzy():
    # exact match
    assert match_string_prefix_fuzzy("The quick brown fox", "The quick") == 9

    # \n and spaces in body
    body = "The\n   quick\nbrown fox"
    prefix = "The quick brown"
    assert match_string_prefix_fuzzy(body, prefix) == 18

    # nospace in body
    body = "Thequickbrownfox"
    prefix = "The quick brown"
    assert match_string_prefix_fuzzy(body, prefix) == 13

    # lots of bad spacing
    body = "  The \n quick\tbrown   fox"
    prefix = " The  quick brown"
    assert match_string_prefix_fuzzy(body, prefix) == 19

    # misalignment (see #TODO in func.
    assert match_string_prefix_fuzzy("Hello world", "Hello Mars") is None

    # prefix longer than body
    assert match_string_prefix_fuzzy("Short", "Short but longer") is None

    # exact match
    assert (
        match_string_prefix_fuzzy(
            "Statute Title\nStatute Name\nRest of text", "Statute Title Statute Name"
        )
        == 26
    )


if __name__ == "__main__":
    test_match_string_prefix_fuzzy()
    test_statute_title_structurer()
    

    TITLE_21_CONSISTENCY_EXCEPTIONS = "§21-1168."
    statute_path = Path("docs") / "statutes"
    parser = StatuteParser(
        pdf_path=statute_path / "2024-21.pdf", cache_dir=statute_path / "cache"
    )
    res = parser.parse()
    exceptions = [""]

    statutes: list[Statute] = []
    for title, name, body, history in res:
        # print(f"Title {title}")
        # print("")
        # print(body)
        if title in TITLE_21_CONSISTENCY_EXCEPTIONS:
            check_consistency = False
        else:
            check_consistency = True
        structured_body = StatuteBodyStructurer().structure(body, check_consistency=check_consistency)
        structured_title = StatuteTitleStructurer().structure(title)

        # print(structured_body)

        # print(len(structured_body))
        st = Statute(title=title, name=name, body=structured_body, history=history)
        statutes.append(st)
        print(st.title, st.directory())
        
        print(st.get_text())

