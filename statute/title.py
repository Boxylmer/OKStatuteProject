import json
from pathlib import Path
from typing import Optional

from statute.statuteparser import StatuteParser
from statute.statute import Statute
from statute.structurers import StatuteBodyStructurer, StatuteReferenceStructurer


class Title:
    def __init__(self, statutes: list[Statute]):
        self.statutes = statutes

        self.reference_registry: dict[str, Statute] = {}
        for statute in statutes:
            key = self._make_registry_key(statute.reference)
            # if key in self.reference_registry:
            #     raise ValueError(f"Duplicate statute reference: {key}")
            self.reference_registry[key] = statute

    def _make_registry_key(self, ref: dict) -> str:
        """Create a unique key from a section reference dict."""
        version = ref.get("version") or ""
        return f"{ref['title'].lower()}|{ref['section'].lower()}|{version.lower()}"

    def get_reference_text(
        self, section_reference: dict, subsection_reference: str = "", **kwargs
    ) -> Optional[str]:
        """
        Given a section reference and a subsection path (e.g., "A.1.b"),
        return the referenced text or None if not found.
        """
        key = self._make_registry_key(section_reference)

        statute = self.reference_registry.get(key)
        if not statute:
            return None

        return statute.get_text(subsection=subsection_reference, **kwargs)

    def save_cache(self, cache_path: Path):
        """Save the title (list of statutes) to a JSON cache file."""
        data = {
            "statutes": [s.to_json() for s in self.statutes],
        }
        cache_path.write_text(json.dumps(data, indent=2))

    @staticmethod
    def from_cache(cache_path: Path) -> "Title":
        """Load a title from a JSON cache file."""
        raw = json.loads(cache_path.read_text())

        statutes = [Statute.from_json(json.loads(s)) for s in raw["statutes"]]
        return Title(statutes)

    @staticmethod
    def from_pdf(
        pdf_path: Path,
        pdf_cache_path=Path("data/pdf_cache"),
        check_exemptions: list[str] = [],
    ) -> "Title":
        """
        Parse a statute PDF file into a structured Title object.

        This method uses internal parsing and structuring logic to transform a statute
        PDF into a Title containing multiple Statute instances. It supports optional
        caching and custom exemptions for consistency checks.

        Args:
            pdf_path (Path): 
                The path to the statute PDF to parse (e.g., 'docs/statutes/2024-21.pdf').
            pdf_cache_path (Path, optional): 
                The directory used to cache parsed output from the PDF parser.
                Defaults to 'data/pdf_cache'.
            check_exemptions (list[str], optional): 
                A list of section references (as strings) that should be exempt from
                consistency checking during body structuring. This should be the literal
                staute section that shows up in the PDF.

        Returns:
            Title: A fully constructed Title instance containing all parsed Statute objects.

        Example:
            >>> Title.from_pdf(
            ...     pdf_path=Path("docs/statutes/2024-21.pdf"),
            ...     check_exemptions=[{"title": "21", "section": "1168", "version": "2024"}]
            ... )

        Notes:
            - Exemptions should only be used for known edge cases that break consistency rules.
        """

        parser = StatuteParser(pdf_path=pdf_path, cache_dir=pdf_cache_path)
        res = parser.parse()

        statutes = []
        for unstructured_reference, name, body, history in res:
            if unstructured_reference in check_exemptions:
                check_consistency = False
            else:
                check_consistency = True
            structured_body = StatuteBodyStructurer().structure(
                body, check_consistency=check_consistency
            )
            reference = StatuteReferenceStructurer().structure(unstructured_reference)
            
            st = Statute(
                reference=reference, name=name, body=structured_body, history=history
            )
            statutes.append(st)
            # print(st.title, st.directory())

            # print(body)
            # print(st.get_text())
            # print(structured_body)
            # print()

        return Title(statutes)

