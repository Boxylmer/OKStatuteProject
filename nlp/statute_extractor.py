import re
import json
from pathlib import Path
from typing import List, Dict, Union
from statute.statutecache import Statute
from nlp.ollama import OllamaChatStream


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


INSTRUCTIONS_STATUTE_STRUCTURER = """
You are a legal parsing assistant. Convert a list of statute lines into structured JSON.

Each node must include:
- "label": section/subsection ID (e.g. A, 1, a). Do not include punctuation.
- "text": content (excluding the label).
- "subsections": list of children (always included, even if empty).

Input:
- A list of raw text lines representing a legal statute. Each line may contain a section heading, a subsection marker (e.g., "A.", "1.", "a.", "(A)", "(1)", etc.), or continuation text.


Requirements:
- The top-level (root) should only include unlabeled text that appears before any labeled sections (like preambles or headers).
- Group lines based on their structural labels. Labels don't necessarily always follow the pattern A.1.a, they might do a.i.1 for example. 
- Preserve the hierarchical relationships implied by the labels.
- Continuation lines (unlabeled lines) do not have a label and are placed according to your best judgement.
- Only parse the latest version for documents with multiple versions and ignore all other versions.
- A subsection ends when you encounter a label from a higher level or see the next expected label in the hierarchy. 

Example Input:
[
  "The following statute defines trade secrets."
  "A. Any person who, with intent to steal or misuse a trade secret:",
  "(a) steals or embezzles an article representing a trade secret;",
  "(b) copies such an article without authority;",
  "is guilty of larceny under Section 1704. Value of the secret determines severity.",
  "B. (a) \"Article\" includes any object, data, or copy thereof.",
  "(b) \"Representing\" means describing or recording.",
  "(c) \"Trade secret\" means info that:",
  "1. Has value from being secret and not easily obtained;",
  "2. Is protected by reasonable efforts to remain secret.",
  "D. Does not apply if a written agreement governs post-employment disputes."
]

Example Output:
{
  "label": "",
  "text": "The following statute defines trade secrets.",
  "subsections": [
    {
      "label": "A",
      "text": "Any person who, with intent to steal or misuse a trade secret:",
      "subsections": [
        {
          "label": "a",
          "text": "Steals or embezzles an article representing a trade secret",
          "subsections": []
        },
        {
          "label": "b",
          "text": "Copies such an article without authority",
          "subsections": []
        }
      ]
    },
    {
      "label": "",
      "text": "Is guilty of larceny under Section 1704. Value of the secret determines severity.",
      "subsections": []
    },
    {
      "label": "B",
      "text": "Definitions",
      "subsections": [
        {
          "label": "a",
          "text": "\"Article\" includes any object, data, or copy thereof",
          "subsections": []
        },
        {
          "label": "b",
          "text": "\"Representing\" means describing or recording",
          "subsections": []
        },
        {
          "label": "c",
          "text": "\"Trade secret\" means info that:",
          "subsections": [
            {
              "label": "1",
              "text": "Has value from being secret and not easily obtained",
              "subsections": []
            },
            {
              "label": "2",
              "text": "Is protected by reasonable efforts to remain secret",
              "subsections": []
            }
          ]
        }
      ]
    },
    {
      "label": "D",
      "text": "Does not apply if a written agreement governs post-employment disputes",
      "subsections": []
    }
  ]
}
Convert this statute: 
"""

INSTRUCTIONS_STATUTE_STRUCTURE = """
You are a legal parsing assistant. Your goal is to convert a list of statute lines scraped from the internet into a JSON template for another person to fill out.

Each node must include:
- "label": section/subsection ID (e.g. A, 1, a). Do not include punctuation.
- "text": content (you don't fill this out).
- "subsections": list of children (always included).

Input:
- A list of raw text lines representing a legal statute. Each line may contain a section heading, a subsection marker (e.g., "A.", "1.", "a.", "(A)", "(1)", etc.), or continuation text.

Requirements:
- If multiple versions of a statute are present, generate a template for only the latest version.
- Group lines based on their structural labels. Labels don't necessarily always follow the pattern A.1.a, they might do a.i.1 for example. 
- Make sure that labels follow the correct order and structure (A, then B, then C, etc)

Example Input:
[
  "The following statute defines trade secrets."
  "A. Any person who, with intent to steal or misuse a trade secret:",
  "(a) steals or embezzles an article representing a trade secret;",
  "(b) copies such an article without authority;",
  "is guilty of larceny under Section 1704. Value of the secret determines severity.",
  "B. (a) \"Article\" includes any object, data, or copy thereof.",
  "(b) \"Representing\" means describing or recording.",
  "(c) \"Trade secret\" means info that:",
  "1. Has value from being secret and not easily obtained;",
  "2. Is protected by reasonable efforts to remain secret.",
  "D. Does not apply if a written agreement governs post-employment disputes."
]

Example Output:
{
  "label": "",
  "text": "...",
  "subsections": [
    {
      "label": "A",
      "text": "...",
      "subsections": [
        {
          "label": "a",
          "text": "...",
          "subsections": []
        },
        {
          "label": "b",
          "text": "...",
          "subsections": []
        }
      ]
    },
    {
      "label": "",
      "text": "...",
      "subsections": []
    },
    {
      "label": "B",
      "text": "...",
      "subsections": [
        {
          "label": "a",
          "text": "...",
          "subsections": []
        },
        {
          "label": "b",
          "text": "...",
          "subsections": []
        },
        {
          "label": "c",
          "text": "...",
          "subsections": [
            {
              "label": "1",
              "text": "...",
              "subsections": []
            },
            {
              "label": "2",
              "text": "...",
              "subsections": []
            }
          ]
        }
      ]
    },
    {
      "label": "D",
      "text": "...",
      "subsections": []
    }
  ]
}


Create a template for this statute: 
"""
 

def extract_statute(statute: Statute, model="qwen3:8b", context_length=16384):
    parsed = generate_statute_summary(statute, model, context_length)
    json = parse_llm_output_to_json(parsed)
    return json


def generate_statute_summary(
    statute: Statute, model="qwen3:8b", context_length=16384, verbose=False
) -> str:
    """Runs the LLM to extract penalties from a statute."""
    statute_text = "### STATUTE: " + statute.formatted_text()
    prompt = INSTRUCTION_PARALEGAL + "\n" + statute_text
    response_stream = OllamaChatStream(
        prompt,
        model=model,
        num_ctx=context_length,
        top_k=1,
        top_p=1,
        temperature=0,
        verbose=verbose,
    )

    response = "".join(response_stream)
    print(response)

    if response_stream.prompt_eval_count + response_stream.eval_count > context_length:
        raise RuntimeError(
            f"LLM query exceeded allowed context length ({context_length}). prompt: {response_stream.prompt_eval_count}, response: {response_stream.eval_count}"
        )
    return response


def parse_llm_output_to_json(llm_output: str) -> Union[List[Dict[str, str]], List]:
    """Attempts to clean LLM output into JSON. Returns an empty list if parsing fails."""
    cleaned = re.sub(r"<think>.*?</think>", "", llm_output, flags=re.DOTALL).strip()
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


def write_statute_json(
    output_folder: Path, citation: str, json_data: Union[List, Dict]
):
    """Writes the JSON data to disk under a consistent filename."""
    output_folder.mkdir(parents=True, exist_ok=True)
    out_path = output_folder / f"{citation}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)
    print(f"✅ Saved: {out_path}")


def extract_json_from_llm_output(llm_output: str) -> dict:
    """
    Extracts the first valid JSON object from a raw LLM output string using a brace counting method.

    Args:
        llm_output: Raw string output from the LLM containing JSON text.

    Returns:
        Parsed JSON object as a Python dict.

    Raises:
        ValueError: If no balanced JSON object is found or JSON parsing fails.
    """
    start_idx = None
    brace_stack = 0

    for i, ch in enumerate(llm_output):
        if ch == "{":
            if start_idx is None:
                start_idx = i
            brace_stack += 1
        elif ch == "}":
            if brace_stack > 0:
                brace_stack -= 1
                if brace_stack == 0 and start_idx is not None:
                    json_str = llm_output[start_idx : i + 1]
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError as e:
                        raise ValueError(f"JSON decoding failed: {e}")

    raise ValueError("No balanced JSON object found in LLM output.")


def format_raw_statute(
    statute: list[str], model="qwen3:8b", context_length=32768, verbose=False
) -> str:
    """Runs the LLM to extract format a statute as a JSON object."""
    prompt = INSTRUCTIONS_STATUTE_STRUCTURER + "\n### STATUTE: " + str(statute)
    response_stream = OllamaChatStream(
        prompt,
        model=model,
        num_ctx=context_length,
        top_k=1,
        top_p=1,
        temperature=0,
        verbose=verbose,
    )

    response = "".join(response_stream)
    tag = "</think>"
    if tag in response:
        response = response.split(tag, 1)[1].lstrip()

    if response_stream.prompt_eval_count + response_stream.eval_count > context_length:
        raise RuntimeError(
            f"LLM query exceeded allowed context length ({context_length}). prompt: {response_stream.prompt_eval_count}, response: {response_stream.eval_count}"
        )

    json_response = extract_json_from_llm_output(response)
    return json_response
