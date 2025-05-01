import os
import json
from datetime import datetime
from statute.statuteparser import StatuteParser


class StatuteCache:
    def __init__(self, cache_folder: str):
        self.cache_folder = cache_folder
        os.makedirs(cache_folder, exist_ok=True)

    def _cache_path(self, title_section: str) -> str:
        return os.path.join(self.cache_folder, f"{title_section}.json")

    def cache_statute(self, statute_link: str) -> StatuteParser:
        # Download and parse the statute directly from the link
        parser = StatuteParser.from_oscn(statute_link)

        data = {
            "link": statute_link,
            "title_section": f"{parser.full_title}.{parser.full_section}",
            "cached_at": datetime.now().strftime("%Y%m%d"),
            "html": parser.formatted_text(),  # or raw html if you change this later
        }

        with open(self._cache_path(data["title_section"]), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return parser

    def available_statutes(self) -> list[str]:
        return [
            f.removesuffix(".json")
            for f in os.listdir(self.cache_folder)
            if f.endswith(".json")
        ]

    def get_statute(self, title_section: str) -> StatuteParser:
        path = self._cache_path(title_section)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Statute {title_section} not cached.")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return StatuteParser.from_html(data["html"])


# from statute.statuteparser import StatuteParser

# class StatuteCache:
#     # Cache a set of html documents based on title and statute
#     # Get the html document, construct a StatuteScraper
#     # Save the link itself / way of determining if we've cached this before
#     # Decide on some kind of structure to house the statutes in (folder?) with their
#     # link, title.section, date (yyyy-mm-dd), html
#     # JSON!

#     # So really I think the cache for each statute is a json doc with a link, title.section, datetime cached, and the html text or raw texts  (one or the other, probably the raw html if we can load it well)
#     def __init__(self, cache_folder: str):
#         ...
#         # if the cache folder doesn't exist, create it

#     def cache_statute(self, statute_link: str) -> StatuteParser:
#         return StatuteParser("foo", "bar", [])
#         # grab, cache the statute, return the parsed Statute

#     def available_statutes(self):
#         list[str]
#         # read and list

#     # need some kind of iteration that also has a filter for title (statutes only from title 21, returning the most recent or ALL statutes)

#     def get_statute(self):
#         ...

#     # method to delete old statutes


#     # what else? recall the ultimate goal is to do two things: Format the statutes in a way we can generate documents from them, and train a rag
