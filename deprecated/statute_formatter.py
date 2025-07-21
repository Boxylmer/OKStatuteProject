from collections import Counter
import json
import textwrap
import re
from typing import List, Dict

from nlp.ollama import OllamaChatStream
from nlp.utils import extract_json


def normalize_word_counts(text: str) -> Counter:
    """
    Normalize text by extracting alphanumeric words and counting occurrences.
    """
    words = re.findall(r"\b[a-zA-Z0-9]+\b", text)
    return Counter(words)


def find_missing_words(original: str, copied: str) -> List[str]:
    """
    Return a list of words that were in `original` but missing from `copied`.
    Repeats words based on how many times they are missing.
    """
    raw_counts = normalize_word_counts(original)
    parsed_counts = normalize_word_counts(copied)
    missing = []
    for word, count in raw_counts.items():
        diff = count - parsed_counts[word]
        if diff > 0:
            missing.extend([word] * diff)
    return missing


def find_extra_words(original: str, copied: str) -> List[str]:
    """
    Return a list of words that appear extra in `copied` compared to `original`.
    Repeats words based on how many extra times they occur.
    """
    raw_counts = normalize_word_counts(original)
    parsed_counts = normalize_word_counts(copied)
    extra = []
    for word, count in parsed_counts.items():
        diff = count - raw_counts[word]
        if diff > 0:
            extra.extend([word] * diff)
    return extra


def check_copy_loss(
    raw: str, parsed: List[Dict[str, str]], verbose: bool = False
) -> tuple[List[str], List[str]]:
    """
    Check for missing or extra words between the raw input and the parsed output.

    Args:
        raw: The original raw string.
        parsed: A list of parsed items, each a dict with optional 'label' and 'text'.
        verbose: Whether to print a summary of detected issues.

    Returns:
        (missing, extra): A tuple of lists of missing and extra words.
    """
    parsed_text = " ".join(
        (item.get("label", "") + " " + item.get("text", "")).strip() for item in parsed
    ).strip()

    missing = find_missing_words(raw, parsed_text)
    extra = find_extra_words(raw, parsed_text)

    if verbose:
        if missing:
            print("\n--> PROOFREADING: ⚠️  Missing words detected:")
            for word in missing:
                print(f"- {word}")
        else:
            print("\n--> PROOFREADING: ✅ No missing words.")

        if extra:
            print("\n--> PROOFREADING: ⚠️  Extra words detected:")
            for word in extra:
                print(f"+ {word}")
        else:
            print("\n--> PROOFREADING: ✅ No extra words.")

    return missing, extra


def is_compound_typo(missing_words: list[str], extra_words: list[str]) -> bool:
    """
    Returns True if a single missing word appears to be a compound that was split
    into two or more extra words.
    Example: missing = ["consumealcoholic"], extra = ["consume", "alcoholic"]
    """
    if len(missing_words) != 1 or len(extra_words) < 2:
        return False

    missing = missing_words[0].lower()
    extra_joined = "".join(extra_words).lower()

    return missing == extra_joined


def common_issue(missing_words: list[str], extra_words: list[str]) -> bool:
    if is_compound_typo(missing_words, extra_words):
        return True

    return False


class StatuteFormatter:
    MAX_RETRIES = 3

    def __init__(
        self,
        model: str,
        context_length: int,
        proofread: bool = False,
        verbose: bool = False,
    ):
        """
        Initialize the formatter with model and formatting options.
        """
        self.model = model
        self.context_length = context_length
        self.proofread = proofread
        self.verbose = verbose

    @staticmethod
    def clean_statute_input(lines: List[str]) -> List[str]:
        """
        Replace problematic characters and strip whitespace from input lines.
        """
        return [
            line.replace("\x93", "'").replace("\x94", "'").replace('"', "'").strip()
            for line in lines
        ]

    @staticmethod
    def extract_response(response: list | dict) -> list[dict[str, str]]:
        json_output = extract_json(response)[-1]
        if isinstance(json_output, dict):
            json_output = [json_output]

        for json_item in json_output:
            if "label" not in json_item:
                raise ValueError(f"label field not present in line: {json_item}.")

            if "text" not in json_item:
                raise ValueError(f"text field not present in line: {json_item}.")

        return json_output

    def _first_draft_prompt_single_line(self, raw_line: str) -> tuple[str, str]:
        system = textwrap.dedent("""
            /no_think
            Instructions:
            You are parsing statute text. Your job is to take a statute line and parse it into a json entry.

            Rules:
            1. All the text should be copies either into the label or text field. Nothing should be reworded or omitted except for label punctuation. 
            2. Statutes that do not used labeled lists are parsed as {"label": "", "text": "[text]"}.
            3. Only copy the alphanumeric component of the label. e.g., "A." becomes "A", "(1):" becomes "1".
            4. Nested labels can be separated with a "." in the label field. E.g., "A. 1:" becomes "A.1"
            5. If multiple labels are in a line e.g., "a. the law is this and b. the law is that", then make sure you put the parsed lines in a list [{"label": "[label]", "text": "[text]"}, ...]
            6. Do not fix typos. 

            Example Input:
                A. 1. This statute is enforced for Bucks county

            Output:
                {"label": "A.1", "text": "This statute is enforced for Bucks county"}
        """)

        user = textwrap.dedent(f"""
            Parse the following statute:
            {raw_line}
        """)
        return system, user

    def _line_proofing_prompt(
        self,
        raw_line: str,
        output_lines: dict[str, str],
        missing_words: list[str],
        extra_words: list[str],
    ) -> tuple[str, str]:
        system = textwrap.dedent("""
            /no_think
            You are a legal text proofreader that ensures each parsed line of statute text is formatted correctly.
            You are given the STATUTE_TEXT and PARSED_LINE and are expected to output the proofread line in json.

            The format of the json is a dictionary with exactly two keys:
            - "label": a string (possibly empty) that should only contain a short identifier like "A", "1", "a", etc.
            - "text": the statute text associated with the label

            Your job is to:
            - Ensure the output is in this format: {"label": "<label>", "text": "<text>"} (with both as strings)
            
            - Extract any subsection label from the beginning of "text" (e.g., {label: "", text: "B. The law..."} should be {label: "B", text: "The law..."})
            - Take any words present in MISSING_WORDS and ensure the parsed text has them in the right place. 
            - Take and words present in EXTRA_WORDS and ensure they're removed from the parsed text. 
            - If multiple labels are in a line e.g., "a. the law is this and b. the law is that", then leave the label field empty and copy the text verbatim.
            - Make sure that the first pass didn't get overzealous and fix typos. 
            
            Rules:
            1. All the text should be copies either into the label or text field. Nothing should be reworded or omitted except for label punctuation. 
            2. Statutes that do not used labeled lists are parsed as {"label": "", "text": "[text]"}.
            3. Only copy the alphanumeric component of the label. e.g., "A." becomes "A", "(1):" becomes "1".
            4. Nested labels can be separated with a "." in the label field. E.g., "A. 1:" becomes "A.1"
            5. If multiple labels are in a line e.g., "a. the law is this and b. the law is that", then make sure you put the parsed lines in a list [{"label": "[label]", "text": "[text]"}, ...]
            6. Do not fix typos. 

            
            Examples: 
            {"label": "1", "text": "1. foobar baz"} -> {"label": "1", "text": "foobar baz"} # duplicate label
            {"label": "", "text": "1. foobar baz"} -> {"label": "1", "text": "foobar baz"} # label wasn't in the right place
            {"label": "1", "text": "foobar baz"} -> {"label": "1", "text": "foobar baz"} # no change needed
            
            
        """)
        user = textwrap.dedent(f"""
            Proofread this statute text:
            
            STATUTE TEXT: {raw_line}                   
            
            PARSED_LINE: {json.dumps(output_lines)}
            
            MISSING_WORDS: {missing_words}   

            EXTRA_WORDS: {extra_words}
            
        """)

        return system, user

    def _run_ollama(
        self, system_prompt: str, user_prompt: str, primer: str = "", temperature=0
    ) -> OllamaChatStream:
        return OllamaChatStream(
            user_prompt,
            system=system_prompt,
            model=self.model,
            num_ctx=self.context_length,
            top_k=1,
            top_p=1,
            temperature=temperature,
            verbose=self.verbose,
            primer=primer,
        )

    def process_statute_line_by_line(
        self, raw_statute: list[str]
    ) -> list[dict[str, str]]:
        """
        Format a list of raw statute lines into structured label/text pairs using an LLM.
        Optionally performs a proofreading pass to fix label placement and cleanup.
        """
        if self.verbose:
            print("_______________________________________")
            print("--> Parsing the following statute text:")
            print(raw_statute)

        cleaned_lines = self.clean_statute_input(raw_statute)
        parsed_lines = []
        for raw_line in cleaned_lines:
            system_prompt, user_prompt = self._first_draft_prompt_single_line(raw_line)
            if self.verbose:
                print()
                print(f"--> Working on line: {raw_line}")
                print("--> LLM output (first pass)")
            response = self._run_ollama(
                system_prompt=system_prompt, user_prompt=user_prompt, primer="Output: "
            )
            lines_in_string = self.extract_response(response)

            missing_words, extra_words = check_copy_loss(
                raw_line, lines_in_string, verbose=self.verbose
            )

            for n in range(self.MAX_RETRIES):
                if not (missing_words or extra_words):
                    break

                if is_compound_typo(
                    missing_words=missing_words, extra_words=extra_words
                ):
                    missing_words = []
                    extra_words = []
                    break

                print(f"Initial pass failed. Retrying (attempt {n}/{self.MAX_RETRIES})")
                system_prompt, user_prompt = self._line_proofing_prompt(
                    raw_line=raw_line,
                    output_lines=lines_in_string,
                    missing_words=missing_words,
                    extra_words=extra_words,
                )
                if self.verbose:
                    print()
                    print("--> LLM output (proofreading pass)")
                response = self._run_ollama(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    primer="Output: ",
                    temperature=n * 0.1,
                )
                lines_in_string = self.extract_response(response)

                missing_words, extra_words = check_copy_loss(
                    raw_line, lines_in_string, verbose=self.verbose
                )

            if missing_words:
                raise ValueError("Missing words in proofread response: ", missing_words)

            if extra_words:
                raise ValueError("Extra words in proofread response: ", extra_words)

            for line in lines_in_string:
                if not line["label"] and not line["text"]:
                    if self.verbose:
                        print("--> LINE WAS EMPTY")
                    continue
                else:
                    parsed_lines.append(line)

        return parsed_lines


class StatutePostprocessor:
    """Aggregate the statutes into structured data"""

    def __init__(
        self,
        # model: str,
        # context_length: int,
        # proofread: bool = False,
        # verbose: bool = False,
    ):
        pass
        # self.model = model
        # self.context_length = context_length
        # self.proofread = proofread
        # self.verbose = verbose

    # goals: Take in the statute, for each line which has a subsequent line after it with no label, determine if that line is "trailing text" or a continuation of the sentence (and thus should be joined to it)
    # e.g, any line with no label that's just "and" should be lumped into the previous line, as well as probably most other one-word things.

    # goal: (maybe we don't need an llm for this) determin if a line denotes the start of a new version of the statute. Find the latest version, remove all lines from previous versions.
    # version text kind of looks like this "Version 2 (Amended by Laws 2024, HB 3157, c. 267, § 2, eff. November 1, 2024)", but just like everything else in OSCN, are super inconsistent and often have other formats I can't predict.

    def log_unlabeled_line_lengths(
        self, parsed_statute: list[dict[str, str]]
    ) -> list[int]:
        lengths = []

        for i, item in enumerate(parsed_statute):
            if item["label"] == "":
                lengths.append(len(item["text"]))

        # distribution = Counter(lengths)

        # print("Unlabeled line length distribution (excluding first line):")
        # for length, count in sorted(distribution.items()):
        #     print(f"  Length {length:>3}: {count} line(s)")

        return lengths
