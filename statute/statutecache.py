import os
import json
from datetime import datetime, date
from pathlib import Path
from statute.statuteparser import StatuteParser
from typing import Any


class StatuteCache:
    def __init__(self, cache_folder: str):
        self.cache_folder = cache_folder
        os.makedirs(cache_folder, exist_ok=True)

        self._load_cached_metadata()

    def _cache_path(self, title_section: str) -> Path:
        return Path(os.path.join(self.cache_folder, f"{title_section}.json"))

    def _load_cached_metadata(self):
        self.cached_links: dict[str, str] = {}  # link -> title_section
        self.cache_dates: dict[str, str] = {}   # title_section -> cached_at
        self.title_sections: set[str] = set()

        for filename in os.listdir(self.cache_folder):
            if not filename.endswith(".json"):
                continue
            title_section = filename.removesuffix(".json")
            try:
                with open(self._cache_path(title_section), "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.cached_links[data["link"]] = title_section
                    self.cache_dates[title_section] = data["cached_at"]
                    self.title_sections.add(title_section)
            except Exception as e:
                print(f"Warning: Skipping corrupt cache file {filename}: {e}")

    def get_statute(self, statute_link: str, force: bool = False) -> StatuteParser:
        title_section = self.cached_links.get(statute_link)
        if title_section and not force:
            return self.get_statute_by_title_section(title_section)

        parser = StatuteParser.from_oscn(statute_link)
        title_section = f"{parser.parse_title()[0]}.{parser.parse_section()[0]}"

        data: dict[str, Any] = {
            "link": statute_link,
            "full_title": parser.full_title,
            "full_section": parser.full_section,
            "title_section": ???
            "cached_at": datetime.now().strftime("%Y%m%d"),
            "raw_texts": parser.raw_text,
        }

        with open(self._cache_path(title_section), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        # Update in-memory metadata
        self.cached_links[statute_link] = title_section
        self.cache_dates[title_section] = data["cached_at"]
        self.title_sections.add(title_section)

        return parser

    def get_statute_by_title_section(self, title_section: str) -> StatuteParser:
        path = self._cache_path(title_section)
        if not path.exists():
            raise FileNotFoundError(f"Statute {title_section} not cached.")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return StatuteParser(
            full_title=title_section.split(".")[0],
            full_section=title_section.split(".")[1],
            raw_texts=data["raw_texts"],
        )

    def available_statutes(self) -> list[str]:
        return sorted(list(self.title_sections))

    def prune_cache(self, cutoff: date | datetime) -> int:
        cutoff_str = cutoff.strftime("%Y%m%d")

        removed = 0
        for title_section in list(self.title_sections):
            cached_at = self.cache_dates.get(title_section)
            if cached_at and cached_at < cutoff_str:
                try:
                    os.remove(self._cache_path(title_section))
                    self.title_sections.remove(title_section)

                    # update link and date mappings
                    for link, ts in list(self.cached_links.items()):
                        if ts == title_section:
                            del self.cached_links[link]
                    del self.cache_dates[title_section]
                    removed += 1
                except Exception as e:
                    print(f"Error deleting {title_section}: {e}")

        return removed











# import os
# import json
# from datetime import datetime
# from pathlib import Path
# from statute.statuteparser import StatuteParser
# from typing import Any


# class StatuteCache:
#     # folder structure should be simple, just the cache folder -> json docs. 
#     # root dir
#     # - json documents (see _cache_path)
#     def __init__(self, cache_folder: str):
#         # initialize the cached links, and make sure our folder structure exists at the cache_folder
#         self.cache_folder = cache_folder
#         os.makedirs(cache_folder, exist_ok=True)

#         # keep track of the links we already have in this cache (load them on init after we've ensured the dirs)
#         cached_links: dict[str, datetime] = {}
#         links_to_title_section: dict[str, str] = {} # used later for quickly getting lists of statutes.

#     def _cache_path(self, title_section: str) -> Path:
#         # given a title_section string (e.g., 21.30a), get the path that you would write the json file to.
#         return Path(os.path.join(self.cache_folder, f"{title_section}.json"))

#     def get_statute(self, statute_link: str, force=False) -> StatuteParser:
#         # if the link was in the cache, download and store it. Otherwise, load it from the cache
#         # force should force a deletion -> re storage of the link 
#         # good start is jsut _cache_path(...).exists()
#         parser = StatuteParser.from_oscn(statute_link)

#         # the cache data should reflect this structure. 
#         # Link (text, a url) 
#         # the title_section string, used for the date / parsing.
#         # the date string (not datetime) used for knowing when we cached the data
#         # the raw texts (list of strings) parsed from the cache at the time. 
#         #  
#         data: dict[str, Any] = {
#             "link": statute_link,
#             "title_section": f"{parser.parse_section()[0]}.{parser.parse_title()[0]}",
#             "cached_at": datetime.now().strftime("%Y%m%d"),
#             "raw_texts": parser.raw_text,  
#         }

#         with open(self._cache_path(data["title_section"]), "w", encoding="utf-8") as f:
#             json.dump(data, f, indent=2)

#         return parser

#     def available_statutes(self) -> list[str]:
#         # return a list of statute names by their title_section json
#         return [
#             f.removesuffix(".json")
#             for f in os.listdir(self.cache_folder)
#             if f.endswith(".json")
#         ]

#     # needs to reconcile with previous getter
#     def get_statute(self, title_section: str) -> StatuteParser:
#         path = self._cache_path(title_section)
#         if not os.path.exists(path):
#             raise FileNotFoundError(f"Statute {title_section} not cached.")

#         with open(path, "r", encoding="utf-8") as f:
#             data = json.load(f)

#         return StatuteParser.from_html(data["html"])

#     def prune_cache(self, cutoff: datetime.date | datetime) -> int:
#         ...
#         # is this the right type signature? Given a datetime, remove all statutes before this datetime and return the number of statutes removed