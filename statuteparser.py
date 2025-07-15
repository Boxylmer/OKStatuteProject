import hashlib
import json
from pathlib import Path
import re
from typing import List, Dict, Tuple, Union, Any
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
        # statute_components = [self._segment_statute_text(s_text, toc_entry) for s_text, toc_entry in zip(statute_texts, statute_names)]
        # print(statute_texts[5])  # Debug stub.

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

        # print("________________________")
        # print(raw_statute_body)
        # print("...")

        # Remove title
        if not raw_statute_body.startswith(statute_title):
            raise ValueError(
                f"Statute number '{statute_title}' not found at start of '{raw_statute_body}'"
            )
        statute_body = raw_statute_body[len(statute_title) :].strip()

        # print(statute_body)
        # print("...")

        match_end = match_string_prefix_fuzzy(body=statute_body, prefix=statute_name)
        if match_end is None:
            raise ValueError(
                f"Statute name '{statute_name}' not found at start of statute body (fuzzy match).\n'{statute_body}'"
            )

        statute_body = statute_body[match_end:].lstrip()

        # print(statute_body)
        # print("...")
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

        # print(statute_body)
        # print("...")
        # print(historical_data)
        # print("__________________________")
        # print("________________________")
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

        return list(
            zip(
                toc_titles,
                clean_names,
                unstructured_clean_bodies,
                clean_historical_data,
            )
        )

    # def _structure_statute_text(self, statute_text: str) -> dict:
    #     """
    #     Convert a single statute string into structured JSON with nested subsections.
    #     Extracts history/notes as a separate field.
    #     """
    #     import re

    #     # Patterns for subsection labels (A, 1, a, i, etc.)
    #     label_patterns = [
    #         (r"^[A-Z]\.", "alpha"),
    #         (r"^\d+\.", "numeric"),
    #         (r"^[a-z]\.", "lower"),
    #         (r"^i{1,3}v?|iv|ix|x{1,3}\.", "roman")  # naive roman numerals
    #     ]

    #     history_lines = []
    #     body_lines = []
    #     in_history = False

    #     for line in statute_text.strip().splitlines():
    #         line = line.strip()
    #         if not line:
    #             continue
    #         if re.match(r"^(Added|Amended|Repealed|NOTE:)", line):
    #             in_history = True
    #         if in_history:
    #             history_lines.append(line)
    #         else:
    #             body_lines.append(line)

    #     # Helper to normalize labels (remove dot or parens)
    #     def normalize_label(raw):
    #         return raw.strip("().").strip()

    #     # Build tree
    #     root = {"label": "", "text": "", "subsections": []}
    #     stack = [root]

    #     for line in body_lines:
    #         label = None
    #         text = line

    #         for pattern, _ in label_patterns:
    #             match = re.match(pattern, line)
    #             if match:
    #                 label = normalize_label(match.group())
    #                 text = line[match.end():].strip()
    #                 break

    #         if label is None:
    #             # continuation of previous text
    #             stack[-1]["text"] += " " + line
    #             continue

    #         # Determine depth
    #         if re.match(r"^[A-Z]$", label):
    #             level = 1
    #         elif re.match(r"^\d+$", label):
    #             level = 2
    #         elif re.match(r"^[a-z]$", label):
    #             level = 3
    #         elif re.match(r"^i{1,3}v?$|^x{1,3}$", label):  # roman
    #             level = 4
    #         else:
    #             level = len(stack)  # fallback

    #         # Truncate or extend stack to the correct depth
    #         stack = stack[:level]
    #         new_node = {"label": label, "text": text, "subsections": []}
    #         stack[-1]["subsections"].append(new_node)
    #         stack.append(new_node)

    #     return {
    #         "label": root["label"],
    #         "text": root["text"],
    #         "subsections": root["subsections"],
    #         "history": "\n".join(history_lines).strip()
    #     }


class StatuteStructurer:
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
        (r"^[ ]{0,3}([A-Z]\.)", "alpha_upper"),   # A. B. C.
        (r"^[ ]{0,3}(\d+\.)", "numeric"),        # 1. 2. 3.
        (r"^[ ]{0,3}([a-z]\.)", "alpha_lower"),   # a. b. c.
    ]

    def __init__(self):
        self.structure = []
        self.stack = []
        self.level_order = [] 

    def structure_statute(self, text: str) -> List[Dict[str, Any]]:
        lines = text.strip().splitlines()
        for line in lines:
            label, label_level, content = self._extract_label(line)
            if label:
                self._push_section(label, label_level, content)
            else:
                self._append_to_last(line)
        return self.structure

    def _extract_label(self, line: str) -> tuple[str, str, str]: # [label name (A, 1, etc)], [label level (1, 2, 3)], [line body]
        for pattern, label_type in self.MARKER_PATTERNS:
            match = re.match(pattern, line)
            if match:
                label = match.group(1)
                content = line[match.end():].strip()
                if label_type not in self.level_order:
                    self.level_order.append(label_type)
                return label, label_type, content
        return '', '', line.strip()

    def _push_section(self, label: str, label_type: str, content: str):
        level = self.level_order.index(label_type)
        section = {"label": label, "text": content, "subsections": []}

        while len(self.stack) > level:
            self.stack.pop()

        if not self.stack:
            self.structure.append(section)
        else:
            self.stack[-1]["subsections"].append(section)

        self.stack.append(section)

    def _append_to_last(self, line: str):
        if self.stack:
            self.stack[-1]["text"] += " " + line.strip()
        elif self.structure:
            self.structure[-1]["text"] += " " + line.strip()
        else:
            self.structure.append({"label": "", "text": line.strip(), "subsections": []})

    def _check_consistency(self, sections: List[Dict[str, Any]]):
        "Did I actually get something in the right order? I.e., A->B->1->2->C->1->2..."
        for level_sections in [sections]:
            self._check_recursive(level_sections)

    def _check_recursive(self, sections: List[Dict[str, Any]]):
        # I don't know a better way to do this than a virtually unreadable recursion function 
        # TODO find out if best practice is to put this function inside _check_consistency

        # TODO this currently fails. search "No corporation or labor union may" and see things start with 2 and progress without nesting
        labels = [s["label"] for s in sections if s["label"]]
        if all(label.endswith(".") for label in labels):
            base_labels = [label[:-1] for label in labels]
            if all(b.isdigit() for b in base_labels):
                nums = list(map(int, base_labels))
                if nums != sorted(nums):
                    raise ValueError(f"Inconsistent numeric label order: {labels}")
            elif all(len(b) == 1 and b.isalpha() for b in base_labels):
                ords = list(map(lambda c: ord(c.lower()), base_labels))
                if ords != sorted(ords):
                    raise ValueError(f"Inconsistent alphabetic label order: {labels}")
        for section in sections:
            self._check_recursive(section["subsections"])


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

    print("All fuzzy string matching tests passed.")


if __name__ == "__main__":
    test_match_string_prefix_fuzzy()
    # parse title 21
    statute_path = Path("docs") / "statutes"
    parser = StatuteParser(
        pdf_path=statute_path / "2024-21.pdf", cache_dir=statute_path / "cache"
    )
    res = parser.parse()

    for title, name, body, history in res:
        print(f"Title {title}:")
        print(body)
        print("")
        print(StatuteStructurer().structure_statute(body))
        print("________________")
