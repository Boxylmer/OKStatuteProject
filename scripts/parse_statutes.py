from statute.statuteparser import StatuteParser
from statute.statutecache import StatuteCache

STATUTE_21_URL = "https://www.oscn.net/applications/oscn/index.asp?ftdb=STOKST21"


cache = StatuteCache("data")
title_21_links = [st["link"] for st in StatuteParser.get_statute_links(STATUTE_21_URL)]
for link in title_21_links:
    parser = cache.get_statute(link)
    print("Cached:", parser.parse_citation())