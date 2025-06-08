from pathlib import Path

from statute.statute import Statute
from statute.statutecache import StatuteCache


STATUTE_21_URL = "https://www.oscn.net/applications/oscn/index.asp?ftdb=STOKST21"
CACHE_PATH = Path("data") / "statute_cache"

cache = StatuteCache(CACHE_PATH)
print("Cache created")
title_21_links = [
    st["link"] for st in Statute.get_statute_links(STATUTE_21_URL, verbose=True)
]
print("Statute URL queue created")
for link in title_21_links:
    parser = cache.get_statute(link)
    print("Cached:", parser.parse_citation())

print(cache.available_statutes())
