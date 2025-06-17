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


# def check_copy_loss(
#     raw: List[str], parsed: List[Dict[str, str]], verbose: bool = False
# ) -> list[str]:
#     """Check if any words were lost in the parsing process."""
#     missing = find_missing_words(raw, parsed)
#     if missing:
#         if verbose:
#             print()
#             print(
#                 "--> PROOFREADING: ⚠️  WARNING: Missing words detected during parsing operation!"
#             )
#             for word in sorted(missing):
#                 print(f"- {word}")


#         return list(missing)
#     else:
#         if verbose:
#             print()
#             print(
#                 "--> PROOFREADING: ✅ All words from the original statute are present in the parsed output."
#             )
#         return []
def check_copy_loss(
    raw: List[str], parsed: List[Dict[str, str]], verbose: bool = False
) -> tuple[list[str], list[str]]:
    """
    Check for missing or extra words between the raw input and the parsed output.

    Returns a dict:
        {
            "missing": list of missing words (repeated),
            "extra": list of extra words (repeated)
        }
    """
    raw_text = " ".join(raw)
    parsed_text = " ".join(
        (item.get("label", "") + " " + item.get("text", "")).strip() for item in parsed
    )

    missing = find_missing_words(raw_text, parsed_text)
    extra = find_extra_words(raw_text, parsed_text)

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


class StatuteFormatter:
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
    def remove_empty_lines(list_of_dicts: list[dict]) -> list[dict]:
        "Remove all dicts from a list of dicts in which the dicts have all falsy values."
        cleaned = []
        for item in list_of_dicts:
            if all((v is None or str(v).strip() == "") for v in item.values()):
                continue
            cleaned.append(item)
        return cleaned

    @staticmethod
    def clean_first_pass_output(objs):
        if isinstance(objs, dict):
            objs = [objs]

        for obj in objs:
            if "label" not in obj:
                raise ValueError(f"label field not present in line: {obj}.")

            if "text" not in obj:
                raise ValueError(f"text field not present in line: {obj}.")

        return StatuteFormatter.remove_empty_lines(objs)

    def _first_draft_prompt(self, raw: List[str]) -> tuple[str, str]:
        joined = "\n".join(f"{line}" for line in raw)
        system = textwrap.dedent("""
            Instructions:
            You are parsing statute text. Break it into a series of labeled sections while preserving the text EXACTLY as it is in .

            Rules:
            1. Always enclose the parsed lines in a list -> []
            2. Statutes that do not used labeled lists are parsed as {"label": "", "text": "[text]"}.
            3. Trailing lines that occur after a labeled section are parsed as {"label": "", "text": "[text]"}.
            4. It's possible for one line to contain multiple labeled sections. 
            5. Do not reword the statute. Copy the lines verbatim, including spelling mistakes and punctuation errors.  

            Input:
            
                A. 1. This statute is enforced for Bucks county
                B. The following are considered violations:
                a. Reckless driving
                b. Public endangerment
                c. Negligent discharge
                These are all subsections of section B.

            Output:
            [{"label": "A", "text": ""}, {"label": "1", "text": "This statute is enforced for Bucks county"}, {"label": "B", "text": "The following are considered violations:"}, {"label": "a", "text": "Reckless driving"}, {"label": "b", "text": "Public endangerment"}, {"label": "c", "text": "Negligent discharge"}, {"label": "", "text": "These are all subsections of section B."}]
        """)

        user = textwrap.dedent(f"""
            Parse the following statute:
            {joined}
        """)
        return system, user

    def _first_draft_missing_text(
        self, statute: list[str], previous_result: list[dict], missing_words: list[str]
    ) -> tuple[str, str]:
        system = textwrap.dedent("""
            Instructions:
            You are a statute parsing correction bot.
            You will be given a statute, it's previous parsed result according to the rules below, and a list of issues with that result. 
            Your job is to correct the parsed statute.

            Rules:
            1. Always enclose the parsed lines in a list -> []
            2. Statutes that do not used labeled lists are parsed as {"label": "", "text": "[text]"}.
            3. Trailing lines that occur after a labeled section are parsed as {"label": "", "text": "[text]"}.
            4. It's possible for one line to contain multiple labeled sections. 
            5. Do not reword the statute. Copy the lines verbatim, including spelling mistakes and punctuation errors.                                
        """)

        joined = "\n".join(f"{line}" for line in statute)
        user = textwrap.dedent(f"""
            Raw statute: 
            {joined}

            Previous parsing result: 
            {json.dumps(previous_result)}  

            but missed the following words: 
            {json.dumps(missing_words)}

            Please write the corrected parsed statute.
        """)
        return system, user

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
            5. If multiple labels are in a line e.g., "a. the law is this and b. the law is that", then leave the label field empty and copy the text verbatim.
            

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
        self, raw_line: str, parsed_line: dict[str, str], missing_words: list[str], extra_words: list[str]
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
            
        """)
        user = textwrap.dedent(f"""
            Proofread this statute text:
            
            STATUTE TEXT: {raw_line}                   
            
            PARSED_LINE: {json.dumps(parsed_line)}
            
            MISSING_WORDS: {missing_words}   

            EXTRA_WORDS: {extra_words}
            
        """)

        return system, user

    def _run_ollama(
        self, system_prompt: str, user_prompt: str, primer: str = ""
    ) -> OllamaChatStream:
        return OllamaChatStream(
            user_prompt,
            system=system_prompt,
            model=self.model,
            num_ctx=self.context_length,
            top_k=1,
            top_p=1,
            temperature=0,
            verbose=self.verbose,
            primer=primer,
        )

    def process_statute(self, raw_statute: List[str]) -> List[Dict[str, str]]:
        """
        Format a list of raw statute lines into structured label/text pairs using an LLM.
        Optionally performs a proofreading pass to fix label placement and cleanup.
        """
        if self.verbose:
            print("______________________")
            print("--> Parsing the following statute text:")
            print(raw_statute)

        cleaned_lines = self.clean_statute_input(raw_statute)

        system_prompt, user_prompt = self._first_draft_prompt(cleaned_lines)

        if self.verbose:
            print()
            print("--> LLM output (first draft):")
        first_draft_response = self._run_ollama(system_prompt, user_prompt)

        parsed = self.clean_first_pass_output(extract_json(first_draft_response)[-1])

        if self.verbose:
            print()
            print(
                f"--> First draft parsed using {first_draft_response.total_eval_count} tokens."
            )

        if self.verbose:
            print()
            print("--> Cleaned first-pass output to:")
            print(json.dumps(parsed))

        if self.proofread:
            if self.verbose:
                print()
                print("--> PROOFREADING: Checking parsing continuity...")
            missing_words = check_copy_loss(cleaned_lines, parsed, verbose=self.verbose)
            n_missing_words = len(missing_words)
            progress_history = [n_missing_words]
            while n_missing_words > 0:
                if self.verbose:
                    print(
                        f"--> PROOFREADING: First is missing the following words: {missing_words}. Retrying with clarification..."
                    )
                retry_system, retry_user = self._first_draft_missing_text(
                    raw_statute, parsed, missing_words
                )
                response = self._run_ollama(retry_system, retry_user)
                parsed = self.clean_first_pass_output(extract_json(response)[-1])
                missing_words = check_copy_loss(cleaned_lines, parsed)
                n_new_missing_words = len(missing_words)

                if n_new_missing_words >= n_missing_words:  # we must see improvement
                    extra = ""
                    if not self.verbose:
                        extra = " (Run with verbose=True to see problems)"
                    raise ValueError(
                        f"Attempted to parse statute twice, but could not correct missing entries. Number of missing words progressed as {progress_history} before increasing to {n_new_missing_words} missing words."
                        + extra
                    )
                else:
                    n_missing_words = n_new_missing_words
                    progress_history.append(n_missing_words)

            if self.verbose:
                print("--> PROOFREADING: ✅ Correction succeeded!")

        return parsed

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
        for line in cleaned_lines:
            system_prompt, user_prompt = self._first_draft_prompt_single_line(line)
            if self.verbose:
                print()
                print(f"--> Working on line: {line}")
                print("--> LLM output (first pass)")
            response = self._run_ollama(
                system_prompt=system_prompt, user_prompt=user_prompt, primer="Output: "
            )
            parsed = self.clean_first_pass_output(extract_json(response)[-1])[0]
            missing_words, extra_words = check_copy_loss([line], [parsed], verbose=self.verbose)

            system_prompt, user_prompt = self._line_proofing_prompt(
                raw_line=line, parsed_line=parsed, missing_words=missing_words, extra_words=extra_words
            )
            if self.verbose:
                print()
                print("--> LLM output (proofreading pass)")
            response = self._run_ollama(
                system_prompt=system_prompt, user_prompt=user_prompt, primer="Output: "
            )
            proofread = self.clean_first_pass_output(extract_json(response)[-1])[0]
            
            missing_words, extra_words = check_copy_loss([line], [proofread], verbose=self.verbose)
            
            if missing_words:
                raise ValueError("Missing words in proofread response: ", missing_words)
            
            if extra_words:
                raise ValueError("Extra words in proofread response: ", extra_words)
            
            parsed_lines.append(proofread)

        return parsed_lines
