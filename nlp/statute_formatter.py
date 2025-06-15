import json
import textwrap
from typing import List, Dict, Union

from nlp.ollama import OllamaChatStream
from nlp.utils import extract_json


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
    def clean_lines(lines: List[str]) -> List[str]:
        """
        Replace problematic characters and strip whitespace from input lines.
        """
        return [
            line.replace("\x93", "'").replace("\x94", "'").replace('"', "'").strip()
            for line in lines
        ]

    @staticmethod
    def remove_empty_lines(items: List[Dict]) -> List[Dict]:
        """
        Remove entries that are entirely empty (label and text).
        """
        return [
            item
            for item in items
            if not all((v is None or str(v).strip() == "") for v in item.values())
        ]

    def _first_draft_prompt(self, raw: List[str]) -> tuple[str, str]:
        joined = "\n".join(f'"{line}"' for line in raw)
        system = textwrap.dedent("""
            /no_think
            Instructions:
            You are parsing statute text. Break it into a series of labeled sections.

            Rules:
            1. Always enclose the parsed lines in a list -> []
            2. If a line contains more than one labeled section (e.g., "A. 1. Text..."), break it into multiple items: one for each label.
                - The first gets an empty text if there's nothing but a label.
                - The second (and others) get the remaining content.
            3. Only write the character component of the label, e.g., (a) -> a, 1. -> 1, [ii] -> ii
            4. Many statutes don't use labeled lists, simply parse them as {{"label": "", "text": "[text]"}}.
            5. Trailing lines that occur after a labeled section (see examples) are also parsed as they are in 2.
            6. If labels like “a.” or “b.” appear in the middle of a sentence, treat them as separate items in the same level.
            7. It's possible for one line to contain multiple labeled sections. 

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
                {{"label": "A", "text": ""}},
                {{"label": "1", "text": "This statute is enforced for Bucks county"}},
                {{"label": "B", "text": "The following are considered violations:"}},
                {{"label": "a", "text": "Reckless driving"}},
                {{"label": "b", "text": "Public endangerment"}},
                {{"label": "c", "text": "Negligent discharge"}},
                {{"label": "", "text": "These are all subsections of section B."}}
            ]
        """)

        user = textwrap.dedent(f"""
            Parse the following statute:
            {joined}
        """)
        return system, user
        

    def _line_proofing_prompt(self, raw_line: Dict[str, str]) -> tuple[str, str]:
        system = textwrap.dedent("""
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

            Input:
            {{"label": "This statute", "text": "defines violations"}}
            Output:
            {{"label": "", "text": "This statute defines violations"}}

            Input:
            {{"label": "", "text": "B. The following are considered violations:"}}
            Output:
            {{"label": "B", "text": "The following are considered violations:"}}

            Input:
            {{"label": "(a).", "text": "Reckless driving"}}
            Output:
            {{"label": "a", "text": "Reckless driving"}}

            Input:
            {{"label": "", "text": "These are all subsections of section B."}}
            Output:
            {{"label": "", "text": "These are all subsections of section B."}}

            Input:
            {{"label": "B", "text": "C. This is the next section"}}
            Output:
            {{"label": "C", "text": "This is the next section"}}

        """)
        user = textwrap.dedent(f"""
            Proofread this line:
            {json.dumps(raw_line)}        
        """)

        return system, user

    def _run_ollama(self, system_prompt: str, user_prompt: str, primer: str = "Output: ") -> OllamaChatStream:
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
            print("_____________")
            print("Parsing statute lines:")
            print(raw_statute)

        cleaned_lines = self.clean_lines(raw_statute)
        system_prompt, user_prompt = self._first_draft_prompt(cleaned_lines)
        raw_response = self._run_ollama(system_prompt, user_prompt)
        parsed = extract_json(raw_response)
        parsed = self.remove_empty_lines(parsed)

        if self.verbose:
            print(f"First draft parsed using {raw_response.total_eval_count} tokens.")

        if not self.proofread:
            return parsed

        if self.verbose:
            print("First draft parsed, beginning proofreading...")

        final_entries = []
        for entry in parsed:
            if self.verbose:
                print("Proofing line: ", entry)
            system_prompt, user_prompt = self._line_proofing_prompt(entry)
            proofed_response = self._run_ollama(system_prompt, user_prompt)
            corrected = extract_json(proofed_response)
            final_entries.append(corrected)

        return final_entries
