from typing import List, Dict
import json

import difflib

from nlp.ollama import OllamaChatStream


THINK_TAG = "</think>"

def extract_json(response_stream: OllamaChatStream, check_context_length: int | None = None):
    """
    Extracts the first valid JSON object or array from an LLM response using bracket counting.

    Returns:
        Parsed JSON (dict or list)

    Raises:
        ValueError: If no complete JSON structure is found or decoding fails.
    """
    response = "".join(response_stream)
    if THINK_TAG in response:
        response = response.split(THINK_TAG, 1)[1].lstrip()

    if check_context_length:
        if response_stream.prompt_eval_count + response_stream.eval_count > check_context_length:
            raise RuntimeError(
                f"LLM query exceeded allowed context length ({check_context_length}). "
                f"prompt: {response_stream.prompt_eval_count}, response: {response_stream.eval_count}"
            )


    start_chars = {"{": "}", "[": "]"}
    open_stack = []
    start_idx = None

    for i, ch in enumerate(response):
        if ch in start_chars:
            if not open_stack:
                start_idx = i
            open_stack.append(start_chars[ch])
        elif ch in start_chars.values():
            if open_stack and ch == open_stack[-1]:
                open_stack.pop()
                if not open_stack and start_idx is not None:
                    json_str = response[start_idx : i + 1]
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError as e:
                        raise ValueError(f"JSON decoding failed: {e}")

    raise ValueError("No balanced JSON object or array found in LLM output.")


def format_json_one_line_dicts(data: list[dict]) -> str:
    """
    Format a list of dicts as JSON with:
    - Top-level brackets on their own lines
    - Each dict rendered as a compact single-line JSON object
    - Double braces {{ }} for use inside f-strings
    """
    lines = ["["]
    for item in data:
        compact = json.dumps(item, separators=(",", ": "))
        compact = compact.replace("{", "{{").replace("}", "}}")
        lines.append(f"    {compact},")
    if len(lines) > 1:
        lines[-1] = lines[-1].rstrip(",")
    lines.append("]")
    return "\n".join(lines)


def format_node(node: Dict[str, str]) -> str:
    """Render a node as a single-line string for easy diffing"""
    return json.dumps(node, ensure_ascii=False)

def diff_statute_sections(
    draft: List[Dict[str, str]], 
    refined: List[Dict[str, str]]
) -> str:
    draft_strs = [format_node(n) for n in draft]
    refined_strs = [format_node(n) for n in refined]

    sm = difflib.SequenceMatcher(a=draft_strs, b=refined_strs)
    report = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        elif tag == 'replace':
            for i, j in zip(range(i1, i2), range(j1, j2)):
                report.append(f"[{i}] changed:\n- {draft_strs[i]}\n+ {refined_strs[j]}")
            for i in range(i1 + (j2 - j1), i2):
                report.append(f"[{i}] removed:\n- {draft_strs[i]}")
            for j in range(j1 + (i2 - i1), j2):
                report.append(f"[insert @ {i2}] added:\n+ {refined_strs[j]}")
        elif tag == 'delete':
            for i in range(i1, i2):
                report.append(f"[{i}] removed:\n- {draft_strs[i]}")
        elif tag == 'insert':
            for j in range(j1, j2):
                report.append(f"[insert @ {i1}] added:\n+ {refined_strs[j]}")

    return "\n".join(report)