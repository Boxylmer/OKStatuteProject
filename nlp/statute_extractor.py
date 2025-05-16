import re
import json
from pathlib import Path
from typing import List, Dict, Union
from statute.statutecache import StatuteParser
from nlp.ollama import generate_stream


INSTRUCTION_PARALEGAL = """
### INSTRUCTIONS:
You are a paralegal. Your task is to extract some JSON data when handed a legal statute.

Only output a list with items containing these entries:
"Offense, Fine, Punishment, Restitution, Exceptions, Summary, Type"

ENTRY SPECS:
- Offense: Short, unique summary of the specific conduct. Must be different for each row.
- Fine: [< or > or exact][dollar amount] Be on the lookout for ranges e.g., "< $500", "$500 to $1000". Do not use commas in numbers.
- Punishment: "[time range] [jail / prison]" Use only if duration is explicitly stated. E.g., "30 days jail", "1-2 years prison".
    - use strictly prison or jail time or time ranges when specifying the punishment.
- Restitution: Any other thing the offender must do. Could include suspensions, community service, or administrative actions. Only use if explicitly stated. E.g., "Handgun license suspended for 3 months"
- Exceptions: Include only if the statute lists exceptions explicitly.
    - Exceptions can be thresholds or important conditions said concisely, not just copied sentences. (e.g., "Only when X, Y, or Z")
- Summary: One sentence summary of the statute. 
- Type: "[misdemeanor / felony / N/A]" Use only those terms are used. Otherwise, write "N/A".

STRICT RULES:
- Do NOT infer or guess values. Leave fields as N/A if information is not directly stated in the statute.
- Think carefully about ranges. Is the fine $X, or is it up to $X? Similarly for punishments.
- If multiple rows have similar offenses, include clear qualifiers in the offense name to distinguish them (e.g., “Use of unauthorized card (≤ $500)” and “Use of unauthorized card (>$500)”).
- ALWAYS include all columns in an entry, putting N/A where information is not available.

IF NOTHING IS EXTRACTABLE: Return an empty list -> []
"""


def extract_statute(statute: StatuteParser, model="qwen3:8b", context_length=16384):
    parsed = generate_statute_summary(statute, model, context_length)
    json = parse_llm_output_to_json(parsed)
    return json

def generate_statute_summary(statute: StatuteParser, model="qwen3:8b", context_length=16384, verbose=False) -> str:
    """Runs the LLM to extract penalties from a statute."""
    statute_text = "### STATUTE: " + statute.formatted_text()
    prompt = INSTRUCTION_PARALEGAL + "\n" + statute_text
    response_stream = generate_stream(
        prompt,
        model=model,
        num_ctx=context_length,
        top_k=1,
        top_p=1,
        temperature=0,
        verbose=True
    )

    response = list(response_stream)

    if response["prompt_eval_count"] + response["eval_count"] > context_length:
        raise RuntimeError(f"LLM query exceeded allowed context length ({context_length}). prompt: {response["prompt_eval_count"]}, response: {response["eval_count"]}")
    return response["response"]


def parse_llm_output_to_json(llm_output: str) -> Union[List[Dict[str, str]], List]:
    """Attempts to clean LLM output into JSON. Returns an empty list if parsing fails."""
    cleaned = re.sub(r'<think>.*?</think>', '', llm_output, flags=re.DOTALL).strip()
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            return parsed
        else:
            return []
        
    except json.JSONDecodeError:
        print("WARNING: JSON DECODE FAILED. RAW DATA BELOW")
        print(cleaned)
        return []


def write_statute_json(output_folder: Path, citation: str, json_data: Union[List, Dict]):
    """Writes the JSON data to disk under a consistent filename."""
    output_folder.mkdir(parents=True, exist_ok=True)
    out_path = output_folder / f"{citation}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)
    print(f"✅ Saved: {out_path}")
