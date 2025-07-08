import re
from typing import List, Dict, Optional


LABEL_REGEX = re.compile(r"^(\s*)([A-Za-z0-9]+)[.)]\s+(.*)")  # e.g., A. Text or 1) Text
HISTORY_REGEX = re.compile(r"(?:(Added|Amended|Repealed|NOTE):|Laws \d{4},)")

def clean_label(raw: str) -> str:
    return raw.strip("().")  # Normalize A., (a), 1)

def is_history_line(line: str) -> bool:
    return bool(HISTORY_REGEX.search(line))

def parse_statute_lines(lines: List[str]):
    root = {"label": "", "text": "", "subsections": []}
    stack = [(0, root)]  # (indent_level, node)

    current_text_lines = []

    def flush_text_to_current():
        if current_text_lines:
            stack[-1][1]["text"] += "\n".join(current_text_lines).strip()
            current_text_lines.clear()

    for line in lines:
        if not line.strip():
            continue

        label_match = LABEL_REGEX.match(line)
        if label_match:
            flush_text_to_current()
            indent_spaces, raw_label, rest = label_match.groups()
            label = clean_label(raw_label)
            indent = len(indent_spaces)

            # Find correct parent based on indent
            while stack and stack[-1][0] >= indent:
                stack.pop()

            parent = stack[-1][1]
            node = {"label": label, "text": rest.strip(), "subsections": []}
            parent["subsections"].append(node)
            stack.append((indent, node))
        else:
            current_text_lines.append(line)

    flush_text_to_current()
    return root


def split_body_and_history(statute_text: str) -> (List[str], List[str]):
    lines = statute_text.strip().splitlines()
    if not lines:
        return [], []

    for i in range(len(lines) - 1, -1, -1):
        if is_history_line(lines[i]):
            # Backtrack to first history-related line
            start = i
            while start > 0 and (is_history_line(lines[start - 1]) or not lines[start - 1].strip()):
                start -= 1
            return lines[:start], lines[start:]
    return lines, []


def parse_statute(statute_text: str) -> Dict:
    body_lines, history_lines = split_body_and_history(statute_text)
    structured = parse_statute_lines(body_lines)
    return {
        "structure": structured,
        "history": "\n".join(history_lines).strip()
    }
