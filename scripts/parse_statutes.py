from pathlib import Path

from statute.statuteparser import StatuteParser
from statute.statutecache import StatuteCache

from nlp.ollama import generate

STATUTE_21_URL = "https://www.oscn.net/applications/oscn/index.asp?ftdb=STOKST21"


cache = StatuteCache(Path("data") / "statute_cache")
title_21_links = [st["link"] for st in StatuteParser.get_statute_links(STATUTE_21_URL)]
for link in title_21_links:
    parser = cache.get_statute(link)
    print("Cached:", parser.parse_citation())

cache.available_statutes()

st1 = cache.get_statute_by_citation(cache.available_statutes()[530])
st1.structured_text()
len(st1.formatted_text())
st1.subsection_names()
st1.parse_citation()

lengths = []
for statute_name in cache.available_statutes():
    st_text = cache.get_statute_by_citation(statute_name).formatted_text()
    le = len(st_text)
    lengths.append(le) 
    if le == 50636:
        print(cache.get_statute_by_citation(statute_name).subsection_names())
        
        print(cache.get_statute_by_citation(statute_name).formatted_text())

sorted(lengths)

instruction_paralegal = """
    ### INSTRUCTIONS:
    You are an automated paralegal. Your task is to read a statute and extract any criminal penalties related to fines, punishment, restitution, or offense type into a structured CSV format.

    Only respond in CSV format with the following columns:
    "Offense, Fine, Punishment, Restitution, Exceptions, Notes, Type"

    Definitions:
    - Offense: Short, unique description of the conduct (must be unique per row)
    - Fine: Dollar amount or range (e.g., "Up to 500", "500 to 1000")
    - Punishment: Duration and type of confinement (e.g., "30 days jail", "1 year jail")
    - Restitution: Other penalties (e.g., "community service", "license suspension")
    - Exceptions: Cases where this statute does not apply
    - Notes: Any key conditions (e.g., thresholds like "only if amount exceeds $500")
    - Type: Either "Misdemeanor" or "Felony" or "N/a"

    Rules:
    - Statutes with **tiered punishments** (e.g., based on dollar amount) must be split into multiple rows. Each row's Offense must be labeled distinctly (e.g., "Use of revoked credit card (≤ $500)", "Use of revoked credit card (>$500)").
    - Do not duplicate Offense names across rows. Modify the name to reflect any distinctions.
    - If both fine and jail apply, include both in their columns; use Notes for thresholds or conditional triggers.
    - If **no relevant fines or punishments** are present, respond only with:  
    `No entries`  
    Do not return an empty CSV table.
    - Statutes do not always clarify information. Do not assume something is a felony, for instance.

    Example row:
    Driving while under `the influence (first offense), > 1000, 1–5 years prison, license suspension, applies to alcohol only, first offense only, Misdemeanor
"""
statute = "### STATUTE: " + st1.formatted_text()
prompt = instruction_paralegal + "\n" + statute
response_data = generate(prompt)
print(response_data["response"])
print("Prompt tokens: ", response_data["prompt_eval_count"])
print("Expected p.t.: ", len(prompt.split()) * 4/3)
