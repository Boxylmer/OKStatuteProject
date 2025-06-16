import json
import textwrap
import re
from typing import List, Dict, Set

from nlp.ollama import OllamaChatStream
from nlp.utils import extract_json





def normalize_words(text: str) -> Set[str]:
    """Extract all alphanumeric words (ignoring punctuation and case)."""
    return set(re.findall(r'\b[a-zA-Z0-9]+\b', text.lower()))

def find_missing_words(raw: List[str], parsed: List[Dict[str, str]]) -> Set[str]:
    """Return the set of words present in the raw input but missing from the parsed text."""
    original_words = normalize_words(" ".join(raw))
    parsed_words = normalize_words(" ".join(item.get("text", "") + " ".join(item.get("label", "")) for item in parsed))
    return original_words - parsed_words

def check_copy_loss(
    raw: List[str],
    parsed: List[Dict[str, str]],
    verbose: bool = False
) -> list[str]:
    """Check if any words were lost in the parsing process."""
    missing = find_missing_words(raw, parsed)
    if missing:
        if verbose:
            print("--> PROOFREADING: ⚠️ WARNING: Missing words detected during parsing operation!")
            for word in sorted(missing):
                print(f"- {word}")
    
        return list(missing)
    else:
        if verbose:
            print("--> PROOFREADING: ✅ All words from the original statute are present in the parsed output.")
        return []

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
                return ValueError(f"label field not present in line: {obj}.")

            if "text" not in obj:
                return ValueError(f"text field not present in line: {obj}.")
            
        return StatuteFormatter.remove_empty_lines(objs)  

    def _first_draft_prompt(self, raw: List[str]) -> tuple[str, str]:
        joined = "\n".join(f'{line}' for line in raw)
        system = textwrap.dedent("""
            </no think>
            Instructions:
            You are parsing statute text. Break it into a series of labeled sections.

            Rules:
            1. Always enclose the parsed lines in a list -> []
            2. Only write the character component of the label, e.g., (a) -> a, 1. -> 1, [ii] -> ii
            3. Statutes that do not used labeled lists are parsed as {"label": "", "text": "[text]"}.
            4. Trailing lines that occur after a labeled section are parsed as {"label": "", "text": "[text]"}.
            5. If labels like “a.” or “b.” appear in the middle of a sentence, treat them as separate items in the same level.
            6. It's possible for one line to contain multiple labeled sections. 
            7. Do not reword the statute. Copy the lines verbatim, including spelling mistakes and punctuation errors.

            Input:
            [
                "A. 1. This statute is enforced for Bucks county",
                "B. The following are considered violations:",
                "a. Reckless driving",
                "b. Public endangerment",
                "c. Negligent discharge",
                "These are all subsections of section B."
            ]

            Output:
            [
                {"label": "A", "text": ""},
                {"label": "1", "text": "This statute is enforced for Bucks county"},
                {"label": "B", "text": "The following are considered violations:"},
                {"label": "a", "text": "Reckless driving"},
                {"label": "b", "text": "Public endangerment"},
                {"label": "c", "text": "Negligent discharge"},
                {"label": "", "text": "These are all subsections of section B."}
            ]
        """)

        user = textwrap.dedent(f"""
            Parse the following statute:
            {joined}
        """)
        return system, user

    def _first_draft_missing_text(self, first_draft_prompt_system: str, first_draft_prompt_user: str, previous_result: list[dict], missing_words: list[str]) -> tuple[str, str]:
        user = textwrap.dedent(f"""
            In a previous attempt to parse this statute, you generated the following output: 
            {json.dumps(previous_result)}   
            
            but missed the following words: 
            [{json.dumps(missing_words)}]
                               
        """) + first_draft_prompt_user
        print("DEBUG: MISS PROMPT", user)
        return first_draft_prompt_system, user

    def _line_proofing_prompt(self, raw_line: Dict[str, str]) -> tuple[str, str]:
        system = textwrap.dedent("""
            You are a legal text proofreader that ensures each parsed line of statute text is formatted correctly.

            The input is a dictionary with exactly two keys:
            - "label": a string (possibly empty) that should only contain a short identifier like "A", "1", "a", etc.
            - "text": the statute text associated with the label

            Your job is to:
            - Ensure the output is in this format: {"label": "<label>", "text": "<text>"} (with both as strings)
            - Extract any subsection label from the beginning of "text" (e.g., "B. The law..." -> label: "B", text: "The law...")
            - Strip punctuation and whitespace from labels (e.g., "(a)." -> "a")
            - Remove the label from "text" if it was embedded
            - Return the line unchanged if it's already correct

            ### Examples:

            Input:
            {"label": "This statute", "text": "defines violations"}
            Output:
            {"label": "", "text": "This statute defines violations"}

            Input:
            {"label": "", "text": "B. The following are considered violations:"}
            Output:
            {"label": "B", "text": "The following are considered violations:"}

            Input:
            {"label": "(a).", "text": "Reckless driving"}
            Output:
            {"label": "a", "text": "Reckless driving"}

            Input:
            {"label": "", "text": "These are all subsections of section B."}
            Output:
            {"label": "", "text": "These are all subsections of section B."}

            Input:
            {"label": "B", "text": "C. This is the next section"}
            Output:
            {"label": "C", "text": "This is the next section"}

        """)
        user = textwrap.dedent(f"""
            Proofread this line:
            {json.dumps(raw_line)}        
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
        
        parsed = self.clean_first_pass_output(extract_json(first_draft_response))
        
        if self.verbose:
            print()
            print(f"--> First draft parsed using {first_draft_response.total_eval_count} tokens.")

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
            while n_missing_words > 0:
                if self.verbose:
                    print(f"--> PROOFREADING: First draft was missing the following words: {missing_words}. Retrying with clarification...")
                retry_system, retry_user = self._first_draft_missing_text(system_prompt, user_prompt, parsed, missing_words)
                first_draft_response = self._run_ollama(retry_system, retry_user)
                parsed = self.clean_first_pass_output(extract_json(first_draft_response))
                new_missing_words = check_copy_loss(cleaned_lines, parsed)
                n_new_missing_words = len(new_missing_words)

                if n_new_missing_words >= n_missing_words:
                    extra = ""
                    if not self.verbose:
                        extra = " (Run with verbose=True to see problems)"
                    raise ValueError("Attempted to parse statute twice, but could not correct missing entries." + extra)
                else:
                    n_new_missing_words = n_missing_words
            if self.verbose:
                print("--> PROOFREADING: ✅ Correction succeeded!")
        
        return parsed

        # if self.verbose:
        #     print("First draft parsed, beginning proofreading...")

        # final_entries = []
        # for entry in parsed:
        #     if self.verbose:
        #         print("Proofing line: ", entry)
        #     system_prompt, user_prompt = self._line_proofing_prompt(entry)
        #     proofed_response = self._run_ollama(system_prompt, user_prompt)
        #     corrected = extract_json(proofed_response)
        #     final_entries.append(corrected)

        # return final_entries
