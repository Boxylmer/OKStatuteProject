from pathlib import Path

from statute.statuteparser import StatuteParser
from statute.statutecache import StatuteCache

STATUTE_21_URL = "https://www.oscn.net/applications/oscn/index.asp?ftdb=STOKST21"


cache = StatuteCache(Path("data") / "statute_cache")
title_21_links = [st["link"] for st in StatuteParser.get_statute_links(STATUTE_21_URL)]
for link in title_21_links:
    parser = cache.get_statute(link)
    print("Cached:", parser.parse_citation())

cache.available_statutes()

st1 = cache.get_statute_by_citation(cache.available_statutes()[122])
st1.formatted_text()
st1.subsection_names()
st1.structured_text()
st1.parse_citation()

lengths = []
for statute_name in cache.available_statutes():
    st_text = cache.get_statute_by_citation(statute_name).formatted_text()
    le = len(st_text)
    lengths.append(le) 
    if le == 50636:
        print(cache.get_statute_by_citation(statute_name).subsection_names())
        
        print(cache.get_statute_by_citation(statute_name).formatted_text())



