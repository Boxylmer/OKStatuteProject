import json
from pathlib import Path
from typing import Optional

from statute.statuteparser import StatuteParser
from statute.statute import Statute
from statute.structurers import StatuteBodyStructurer, StatuteReferenceStructurer



# Need to load from a cache path on init, then add functions "load_from_pdf" that will add / update statutes.
# It will need a flag overwrite=True, to either ignore existing statutes or overwrite them (since statutes could have post-load added reference data)
# That way, loading from a cache is the default and loading in parsed statutes is the exception. If we load statutes from a pdf with overwrite=False (default), then we don't risk overwriting tediously found reference text. 
#  


class Title:
    def __init__(self, cache_path: Path = None):
        self.statute_registry: dict[str, Statute] = {}
        self.cache_path = cache_path

        if cache_path:            
            self._ensure_cache()
            self._import_from_cache(cache_path=cache_path)

    def _ensure_cache(self):
        self.cache_path.touch()

    def _add_statute(self, statute: Statute, overwrite: bool = False):
        key = self._make_registry_key(statute.reference)
        
        if key in self.statute_registry:
            if overwrite:
                self.statutes.remove(self.reference_registry[key])        
        else:
            self.statute_registry[key] = statute

    def import_from_pdf(self, 
        pdf_path: Path,
        overwrite: bool = False,
        check_exemptions: list[str] = []):
        """
        Import statutes from a PDF file into the Title object.

        This method uses internal parsing and structuring logic to transform a statute
        PDF into a Title containing multiple Statute instances. It supports optional
        caching and custom exemptions for consistency checks.

        Args:
            pdf_path (Path):
                The path to the statute PDF to parse (e.g., 'docs/statutes/2024-21.pdf').
            overwrite (bool): If True, the method will overwrite any existing statutes in the Title.
            check_exemptions (list[str], optional):
                A list of section references (as strings) that should be exempt from
                consistency checking during body structuring. This should be the literal
                staute section that shows up in the PDF.

        Returns:
            n_statutes (int):
                The number of statutes found in the PDF file.

        Example:
            >>> Title.import_from_pdf(
            ...     pdf_path=Path("docs/statutes/2024-21.pdf"),
            ...     overwrite=True,
            ...     check_exemptions=['§21-1168.1', '§21-1168.2'],
            ... )

        Notes:
            - Exemptions should only be used for known edge cases that break consistency rules or errors in the PDF.
            - Exemptions should be a list of the raw title names, not a structured reference. E.g., '§21-1168.'

        """

        parser = StatuteParser(pdf_path=pdf_path)
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

        for statute in statutes: 
            self._add_statute(statute, overwrite=overwrite)

    def _make_registry_key(self, ref: dict) -> str:
        version = ref.get("version") or ""
        return f"{ref['title'].lower()}|{ref['section'].lower()}|{version.lower()}"

    def get_reference_text(
        self,
        section_reference: dict,
        subsection_reference: Optional[str] = None,
        **kwargs,
    ) -> Optional[str]:
        """
        Given a section reference and a subsection path (e.g., "A.1.b"),
        return the referenced text or None if not found.
        """
        key = self._make_registry_key(section_reference)

        statute = self.statute_registry.get(key)
        if not statute:
            raise (ValueError(f"Statute reference {section_reference} does not exist."))

        return statute.get_text(subsection=subsection_reference, **kwargs)

    def set_statute_references(
        self,
        statute_reference: dict,
        ref_map: dict[str | None, list[dict]], # TODO
    ):
        """
        Set references for multiple subsections in a statute.

        Args:
            statute_reference (dict): Dict like {"title": "21", "section": "1168", "version": "2024"}.
            ref_map (dict): Maps subsection paths (like "A.2") or None (for root) to lists of reference dicts. # TODO
        """
        key = self._make_registry_key(statute_reference)
        statute = self.reference_registry.get(key)
        if not statute:
            raise ValueError(f"Statute reference {statute_reference} not found.")

        statute.set_references(ref_map)

        # self.save_cache(#TODO should be callable from ) 

    def save_cache(self):
        """Save the title (list of statutes) to a JSON cache file."""
        if not self.cache_path:
            raise ValueError("Cache path not set.")
        
        data = {
            "statutes": [s.to_json() for s in self.statutes],
        }
        self.cache_path.write_text(json.dumps(data, indent=2))
   
    def _import_from_cache(self, cache_path: Path, overwrite: bool=False):
        raw = json.loads(cache_path.read_text())
        
        if not raw or not raw["statutes"]:
            return
        
        statutes = [Statute.from_json(json.loads(s)) for s in raw["statutes"]]
    
        for statute in statutes:
            self._add_statute(statute, overwrite=overwrite)


