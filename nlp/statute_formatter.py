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

    def _first_draft_prompt(self, raw: List[str]) -> str:
        joined = "\n".join(f'"{line}"' for line in raw)
        return textwrap.dedent(f"""
            /no_think
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
                "a. Reckless driving",
                "b. Public endangerment",
                "c. Negligent discharge",
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
        """)

    def _line_proofing_prompt(self, raw_line: Dict[str, str]) -> str:
        return textwrap.dedent(f"""
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

            ---

            Now proofread this line:
            {json.dumps(raw_line)}
        """)

    def _run_ollama(self, prompt: str, primer: str = "Output: ") -> OllamaChatStream:
        return OllamaChatStream(
            prompt,
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
        prompt = self._first_draft_prompt(cleaned_lines)
        raw_response = self._run_ollama(prompt)
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
            proofed_prompt = self._line_proofing_prompt(entry)
            proofed_response = self._run_ollama(proofed_prompt)
            corrected = extract_json(proofed_response)
            final_entries.append(corrected)

        return final_entries
