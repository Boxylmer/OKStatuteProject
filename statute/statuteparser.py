import hashlib
import json
from pathlib import Path
import re
from typing import List, Tuple


import pymupdf4llm  # type: ignore

from statute.utils import match_string_prefix_fuzzy

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
        toc_references = [h[0] for h in toc_headers]
        toc_names = [h[1] for h in toc_headers]
        content_headers = [h[0] for h in statute_chunks]
        missing = [h for h in toc_references if h not in content_headers]
        if missing:
            print(f"⚠️ Warning: {len(missing)} TOC headers not found in parsed content.")
            for m in missing[:5]:
                print(f"  Missing: {m}")
            raise ValueError("Statute had missing content")

        clean_names = [
            self._clean_toc_name(name, reference)
            for name, reference in zip(toc_names, toc_references)
        ]

        clean_statute_bodies_and_history = [
            self._clean_statute_body(raw_body, name, reference)
            for raw_body, name, reference in zip(
                raw_statute_bodies, clean_names, toc_references
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
                toc_references,
                clean_names,
                unstructured_clean_bodies,
                clean_historical_data,
            )
        )

