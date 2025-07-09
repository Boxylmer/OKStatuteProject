import hashlib
import json
from pathlib import Path
import re
from typing import List, Tuple
import pymupdf4llm  # type: ignore


class StatuteParser:
    def __init__(self, pdf_path: Path, cache_dir: Path = Path("cache")):
        self.pdf_path = Path(pdf_path)
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.md5_hash = self._compute_md5()
        self.raw_markdown_path = self.cache_dir / f"raw_{self.md5_hash}.md"
        self.cleaned_json_path = self.cache_dir / f"split_{self.md5_hash}.json"

    def parse(self):
        statutes = self._parse_clean()
        print(statutes[0]) # Debug stub.

        return statutes 


    def _compute_md5(self) -> str:
        hasher = hashlib.md5()
        with open(self.pdf_path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _parse_raw(self) -> str:
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

    def _clean_markdown_statute_text(self, markdown_text: str) -> str:
        cleaned_lines = []
        footer_pattern = re.compile(r"^Oklahoma Statutes - Title \d+\. .* Page \d+$")
        for line in markdown_text.splitlines():
            if footer_pattern.match(line.strip()):
                continue
            if line.strip() == "```":
                continue
            cleaned_lines.append(line)
        return "\n".join(cleaned_lines)

    def _split_statutes_by_header(self, md_text: str) -> List[Tuple[str, str]]:
        STATUTE_HEADER_RE = re.compile(r"^§[^\s]+-[^\s]+\.", re.MULTILINE)
        matches = list(STATUTE_HEADER_RE.finditer(md_text))
        statutes = []

        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(md_text)
            header_line = match.group().strip()
            body = md_text[start:end].strip()
            statutes.append((header_line, body))
        return statutes

    def _parse_clean(self) -> List[str]:
        # if self.cleaned_json_path.exists():
        #     return json.loads(self.cleaned_json_path.read_text(encoding="utf-8"))

        md_text = self._parse_raw()
        break_point = self._extract_first_statute_name(md_text)
        parts = md_text.split(break_point)
        assert len(parts) == 3, "Unable to split into header, TOC, contents."
        _, toc, contents = parts
        # Add the breaking character back to the toc and contents.
        toc = break_point + toc
        contents = break_point + contents

        cleaned = self._clean_markdown_statute_text(contents)
        statute_chunks = self._split_statutes_by_header(cleaned)
        statute_bodies = [chunk[1] for chunk in statute_chunks]
        self.cleaned_json_path.write_text(
            json.dumps(statute_bodies, indent=2), encoding="utf-8"
        )

        # Consistency check: TOC headers match actual headers
        toc_cleaned = self._clean_markdown_statute_text(toc)
        toc_headers = [h[0] for h in self._split_statutes_by_header(toc_cleaned)]
        content_headers = [h[0] for h in statute_chunks]
        missing = [h for h in toc_headers if h not in content_headers]
        if missing:
            print(f"⚠️ Warning: {len(missing)} TOC headers not found in parsed content.")
            for m in missing[:5]:
                print(f"  Missing: {m}")
            raise ValueError("Statute had missing content")

        return statute_bodies
    
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



if __name__ == "__main__":
    # parse title 21
    statute_path = Path("data") / "statute"
    parser = StatuteParser(
        pdf_path=statute_path / "2024-21.pdf", cache_dir=statute_path / "cache"
    )
    res = parser.parse()
