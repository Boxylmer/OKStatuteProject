from pathlib import Path

from statute.statuteparser import StatuteParser
from statute.statutecache import StatuteCache

from nlp.ollama import generate

import re
import csv


STATUTE_21_URL = "https://www.oscn.net/applications/oscn/index.asp?ftdb=STOKST21"


cache = StatuteCache(Path("data") / "statute_cache")
title_21_links = [st["link"] for st in StatuteParser.get_statute_links(STATUTE_21_URL)]
for link in title_21_links:
    parser = cache.get_statute(link)
    print("Cached:", parser.parse_citation())

cache.available_statutes()

st1 = cache.get_statute_by_citation(cache.available_statutes()[876])
st1.structured_text()
len(st1.formatted_text())
st1.subsection_names()
st1.parse_citation()

lengths = []
for i, statute_name in enumerate(cache.available_statutes()):
    st = cache.get_statute_by_citation(statute_name)
    if bool(re.fullmatch(r"20[a-zA-Z]", st.parse_section()[0])):
        print("Skipping: ", st.parse_section()[0]) 
        continue
    st_text = st.formatted_text()
    le = len(st_text)
    lengths.append(le) 
    if le == 10984:
        

        # print(cache.get_statute_by_citation(statute_name).subsection_names())
        # print(cache.get_statute_by_citation(statute_name).formatted_text())
        print(i)
        cache.get_statute_by_citation(statute_name).parse_citation()

sorted(lengths)


instruction_paralegal = """
### INSTRUCTIONS:
You are an automated paralegal. Your task is to extract **only explicitly stated** penalties from statutes into JSON data.

Only output a list with items containing these entries:
"Offense, Fine, Punishment, Restitution, Exceptions, Notes, Type"

COLUMN RULES:
- Offense: Short, unique summary of the specific conduct. Must be different for each row.
- Fine: [< or > or exact][dollar amount] Use only if an exact dollar amount or range is stated. E.g., "< $500", "$500 to $1000". Do not use commas in numbers.
- Punishment: "[time range] [jail / prison]" Use only if duration is explicitly stated. E.g., "30 days jail", "1-2 years prison".
    - use strictly "prison" or "jail" when specifying the punishment suffix.
- Restitution: Include only if mentioned (e.g., "license suspension", "community service"). Things that are not time served or fines.
- Exceptions: Include only if the statute lists exceptions explicitly.
- Notes: Any minor caveats or stipulations. Major caveats or stipulations become new rows.
- Type: "[misdemeanor / felony / N/a]" Use only those terms are used. Otherwise, write "N/a".

STRICT RULES:
- Do NOT infer or guess values. Leave fields blank if information is not directly stated in the statute.
- Do NOT duplicate offense names — distinguish them using thresholds or qualifiers.
- Do NOT include dollar signs in Punishment (it's for jail/prison durations only).
- Do NOT output "Felony" unless that word appears in the statute.
- If multiple rows have similar offenses, include clear qualifiers in the Offense name to distinguish them (e.g., “Use of unauthorized card (≤ $500)” and “Use of unauthorized card (>$500)”).
- Notes should summarize thresholds or important conditions concisely, not just copy full statute sentences.
- If the statute doesn't define a crime, but adds conditions to other statutes, denote this in the offense name (Condition: ...)

IF NO PENALTIES:
If the statute does not contain any fines, punishments, or criminal penalties, respond exactly with:
No entries
"""

statute = "### STATUTE: " + st1.formatted_text()
prompt = instruction_paralegal + "\n" + statute
response_data = generate(prompt, model="qwen3:8b", num_ctx=32768/2, top_k=10, top_p=0.5)
print(response_data["response"])
print("Prompt tokens: ", response_data["prompt_eval_count"])
print("Expected p.t.: ", len(prompt.split()) * 4/3)

print("Eval tokens: ", response_data["eval_count"])

text = response_data["response"]

# Remove anything before </think> tag (for clean extraction)
cleaned_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

# Split the text by newlines and filter out any empty lines
lines = [line.strip() for line in cleaned_text.splitlines() if line.strip()]

# Extract the header (first line) and data (subsequent lines)
header = lines[0]  # This is the first line containing the CSV header
data_lines = lines[1:]  # These are the rows that need to be written

# Open the CSV file to write the result
with open('output.csv', 'w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    
    # Write the header row (split the header by commas)
    writer.writerow(header.split(','))
    
    # Process each data line
    for line in data_lines:
        # Handle the case of empty fields (i.e., ",,")
        # Split by '","' to preserve empty fields
        row = line.split(',')

        # Clean the quotes around the first and last elements of the row
        row[0] = row[0].strip('"')
        row[-1] = row[-1].strip('"')

        # For all middle elements, clean up the quotes if they exist
        for i in range(1, len(row)-1):
            row[i] = row[i].strip('"')
        
        # Write the row to the CSV file
        writer.writerow(row)

print("CSV file 'output.csv' has been written successfully.")