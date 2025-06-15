import json
from pathlib import Path
from typing import List, Dict, Union

from nlp.ollama import OllamaChatStream
from nlp.utils import extract_json


def first_draft_prompt(raw: list[str]):
    joined = "\n".join(f'"{line}"' for line in raw)

    return f"""
        Instructions:
        You are parsing statute text. Break it into a series of labeled sections. 

        Rules:
        1. Always enclose the parsed lines in a list -> []
        2. Only treat a label like “A.”, “1.”, or “(a)” as a section header if it appears at the start of a line or clause. Do not skip it even if it appears after a long list — it may start a new section.
        3. Only write the character component of the label, e.g., (a) -> a, 1. -> 1, [ii] -> ii
        4. Many statutes don't use labeled lists, simply parse them as {{"label": "", "text": "[text]"}}.
        5. Trailing lines that occur after a labeled section (see examples) are also parsed as they are in 2.
        6. If labels like “a.” or “b.” appear in the middle of a sentence, treat them as separate items in the same level.

        Input:
        [
            "B. The following are considered violations:",
            "a. Reckless driving"
            "b. Public endangerment"
            "c. Negligent discharge"
            "These are all subsections of section B."
        ]

        Output:
        [
            {{"label": "B", "text": "The following are considered violations:"}},
            {{"label": "a", "text": "Reckless driving"}},
            {{"label": "b", "text": "Public endangerment"}},
            {{"label": "c", "text": "Negligent discharge"}},
            {{"label": "", "text": "These are all subsections of section B."}}
        ]

        Here is the statute:
        STATUTE: 
        {joined}
    """


def line_proofing_prompt(raw_line: dict[str, str]) -> str:
    return f"""
        You are a legal text proofreader that ensures each parsed line of statute text is formatted correctly.

        The input is a dictionary with exactly two keys:
        - "label": a string (possibly empty) that should only contain a short identifier like "A", "1", "a", etc.
        - "text": the statute text associated with the label

        Your job is to:
        - Ensure the output is in this format: {{"label": "<label>", "text": "<text>"}} (with both as strings)
        - Extract any subsection label from the beginning of "text" (e.g., "B. The law..." -> label: "B", text: "The law...")
        - Strip punctuation and whitespace from labels (e.g., "(a)." -> "a")
        - Remove the label from "text" if it was embedded
        - Return the line unchanged if it's already correct

        ### Examples:

        #### Text incorrectly turned into label
        Input:
        {{"label": "This statute", "text": "defines violations"}}
        Output:
        {{"label": "", "text": "This statute defines violations"}}

        #### Label didn't get pulled from text
        Input:
        {{"label": "", "text": "B. The following are considered violations:"}}
        Output:
        {{"label": "B", "text": "The following are considered violations:"}}

        #### Formatting in label
        Input:
        {{"label": "(a).", "text": "Reckless driving"}}
        Output:
        {{"label": "a", "text": "Reckless driving"}}
        
        #### Things are already correct
        Input:
        {{"label": "", "text": "These are all subsections of section B."}}
        Output:
        {{"label": "", "text": "These are all subsections of section B."}}

        #### Label from previous line was pulled
        Input:
        {{"label": "B", "text": "C. This is the next section"}}
        Output:
        {{"label": "C", "text": "This is the next section"}}


        ---

        Now proofread this line:
        {json.dumps(raw_line)}
    """


def clean_input_lines(lines: list[str]) -> list[str]:
    cleaned_lines = []
    for line in lines:
        cleaned_lines.append(
            line.replace("\x93", "'").replace("\x94", "'").replace('"', "'").strip()
        )
    return cleaned_lines


def remove_empty_lines(json: list[dict]) -> list[dict]:
    cleaned = []
    for item in json:
        if all((v is None or str(v).strip() == "") for v in item.values()):
            continue
        cleaned.append(item)
    return cleaned


def format_raw_statute(
    raw_statute: list[str], model, proofread=False, context_length=32768, verbose=False
) -> str:
    """Runs the LLM to extract format a statute as list of lines."""

    if verbose:
        print("_____________")
        print("Parsing: ", str(raw_statute))
        print("Rough draft output: ")

    first_draft_response = OllamaChatStream(
        first_draft_prompt(clean_input_lines(raw_statute)),
        model=model,
        num_ctx=context_length,
        top_k=1,
        top_p=1,
        temperature=0,
        verbose=verbose,
        primer="Output: ",
    )

    first_draft_json = extract_json(first_draft_response)

    cleaned_draft_json = remove_empty_lines(first_draft_json)

    if not proofread:
        return first_draft_json

    if verbose:
        print("rough draft parsed and extractd to JSON, refining: ")

    final_entries = []
    for clean_entry_draft in cleaned_draft_json:
        if verbose:
            print("Proofing line: ", clean_entry_draft)
        proofread_entry_response = OllamaChatStream(
            line_proofing_prompt(clean_entry_draft),
            model=model,
            num_ctx=context_length,
            top_k=1,
            top_p=1,
            temperature=0,
            verbose=verbose,
            primer="Output: ",
        )
        proofread_json_entry = extract_json(proofread_entry_response)
        final_entries.append(proofread_json_entry)

    return final_entries
