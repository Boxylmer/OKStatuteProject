from pathlib import Path

import json
import re

from statute.statuteparser import StatuteParser
from statute.statutecache import StatuteCache
from nlp.statute_extractor import extract_statute


STATUTE_21_URL = "https://www.oscn.net/applications/oscn/index.asp?ftdb=STOKST21"
OUTPUT_FOLDER = Path("data") / "parsed_statute_json"

cache = StatuteCache(Path("data") / "statute_cache")
title_21_links = [st["link"] for st in StatuteParser.get_statute_links(STATUTE_21_URL)]
for link in title_21_links:
    parser = cache.get_statute(link)
    print("Cached:", parser.parse_citation())

cache.available_statutes()

st1 = cache.get_statute_by_citation(cache.available_statutes()[150])
st1.structured_text()
len(st1.formatted_text())
st1.subsection_names()
st1.parse_citation()

lengths = []
queued_statutes = []
for i, statute_name in enumerate(cache.available_statutes()):
    st = cache.get_statute_by_citation(statute_name)
    if bool(re.fullmatch(r"20[a-zA-Z]", st.parse_section()[0])):
        print("Skipping: ", st.parse_section()[0]) 
        continue
    st_text = st.formatted_text()
    le = len(st_text)
    lengths.append(le) 
    if le == 12353: # long one
        print(cache.get_statute_by_citation(statute_name).subsection_names())
        print(cache.get_statute_by_citation(statute_name).formatted_text())
        print(i)
        cache.get_statute_by_citation(statute_name).parse_citation()
    queued_statutes.append(statute_name)


def process_statute(output_folder: Path, citation: str, statute: StatuteParser, model: str):
    output_folder.mkdir(parents=True, exist_ok=True)
    out_path = output_folder / f"{citation}.json"
    
    if out_path.exists():
        print("Skipping: ", citation)
        return

    print("Running: ", citation)
    print("Text: ", statute.formatted_text())
    data = extract_statute(statute, model=model)

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"✅ Saved: {out_path}")


for statute_name in queued_statutes:
    try:
        statute = cache.get_statute_by_citation(statute_name)
        process_statute(OUTPUT_FOLDER, statute_name, statute, model="adrienbrault/saul-instruct-v1:Q4_K_M")
    except Exception as e:
        print("Could not process", statute_name)