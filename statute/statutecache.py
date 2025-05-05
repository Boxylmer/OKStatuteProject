import os
import json
from datetime import datetime
from pathlib import Path
from statute.statuteparser import StatuteParser
from typing import Any


class StatuteCache:
    def __init__(self, cache_path: str | Path):
        self.cache_folder = Path(cache_path)
        os.makedirs(cache_path, exist_ok=True)

        self._load_cached_metadata()

    def _cache_path(self, citation: str) -> Path:
        return Path(os.path.join(self.cache_folder, f"{citation}.json"))

    def _load_cached_metadata(self):
        self.cached_links = {}  # str -> str (link -> citation)
        self.cache_dates = {}  # str -> str (datetime isoformat timespec=seconds) citation -> cached_at
        self.citations = set()  # set[str]

        for filename in os.listdir(self.cache_folder):
            if not filename.endswith(".json"):
                continue
            try:
                with open(self.cache_folder / filename, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    citation_str = data["citation"]
                    self.cached_links[data["link"]] = citation_str
                    self.cache_dates[citation_str] = data["cached_at"]
                    self.citations.add(citation_str)

            except Exception as e:
                print(f"Warning: Skipping corrupt cache file {filename}: {e}")

    def get_statute(self, statute_link: str, force: bool = False) -> StatuteParser:
        citation = self.cached_links.get(statute_link)
        if citation and not force:
            return self.get_statute_by_citation(citation)

        parser = StatuteParser.from_oscn(statute_link)

        citation = parser.parse_citation()

        data: dict[str, Any] = {
            "link": statute_link,
            "full_title": parser.full_title,
            "full_section": parser.full_section,
            "citation": citation,
            "cached_at": datetime.now().isoformat(timespec="seconds"),
            "raw_texts": parser.raw_text,
        }

        with open(self._cache_path(citation), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        # Live registry needs updated
        self.cached_links[statute_link] = citation
        self.cache_dates[citation] = data["cached_at"]
        self.citations.add(citation)

        return parser

    def get_statute_by_citation(self, citation: str) -> StatuteParser:
        path = self._cache_path(citation)
        if not path.exists():
            raise FileNotFoundError(f"Statute {citation} not cached.")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            full_title = data["full_title"]
            full_section = data["full_section"]

        return StatuteParser(
            full_title=full_title,
            full_section=full_section,
            raw_texts=data["raw_texts"],
        )

    def available_statutes(self) -> list[str]:
        "Get list of citations of statutes available in the cache."
        return sorted(list(self.citations))

    def prune_cache(self, cutoff: datetime) -> int:
        cutoff_str = cutoff.isoformat(timespec="seconds")

        removed = 0
        for citation in list(self.citations):
            cached_at = self.cache_dates.get(citation)
            if cached_at and cached_at < cutoff_str:
                try:
                    os.remove(self._cache_path(citation))
                    self.citations.remove(citation)

                    # update link and date mappings
                    for link, ts in list(self.cached_links.items()):
                        if ts == citation:
                            del self.cached_links[link]
                    del self.cache_dates[citation]
                    removed += 1
                except Exception as e:
                    print(f"Error deleting {citation}: {e}")

        return removed
