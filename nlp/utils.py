from typing import List, Dict
import json

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

