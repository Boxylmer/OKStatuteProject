from textwrap import dedent, indent
import json

from nlp.ollama import OllamaChatStream
from statute.statute import Statute
from statute.title import Title
from nlp.utils import extract_json


schema = {
    "description": "A statute reference",
    "type": "object",
    "properties": {
        "section_reference": {
            "type": "object",
            "description": "Reference to a section, containing metadata about the section.",
            "properties": {
                "title": {
                    "type": "string",
                    "description": 'The title of the section. E.g., "21" or "15", they\'re usually, but not always, numbers.',
                },
                "section": {
                    "type": "string",
                    "description": 'The section of the title. Usually it\'s number like, can be "10.1" or "31" or "20Q", etc. Sometimes includes a "v" for versioning, but this gets put in the version section.',
                },
                "version": {
                    "type": "integer",
                    "description": "The version number of the section.",
                },
            },
            "required": ["title", "section", "version"],
        },
        "subsection_reference": {
            "type": "string",
            "description": 'Dot separated reference to a subsection, typically "A.1" or a broader "A", or more specific "C.2.b"',
        },
    },
    "required": ["section_reference", "subsection_reference"],
}


class Referenceinator:
    def __init__(self, title: Title, statute: Statute, llm_model: str):
        self.model = llm_model
        self.title = title
        self.statute = statute

    def generate_prompt(self, snippit):

        schema_text = indent(json.dumps(schema, indent=4), "    " * 4) 
        prompt = dedent(
            f"""
                \\nothink
                You are a legal statute parser. 
                Your goal is to identify a list of references to other statutes in a snippit of text.

                Each reference in the list should follow this json schema
                {schema_text}
                
                Some notes:
                    - Sometimes text might say something like "as defined in section X of this title", you will be given the current title and section of the snippit you're looking at.
                    - Often, a reference to another title might be phrased like "as defined in Section 701.7 of title 21". In this case, you would output a section reference and an empty string for the subsection reference.
                    - Quick example:  as provided for in subsection C of Section 6.1 of Title 17 of the Oklahoma Statutes -> {{section_reference: {{"title": "21", "": "section": "6.1", "version": ""}}, "subsection_reference": "C"}}
            
                    
            The following snippit is from title {self.statute.reference["title"]}, section {self.statute.reference["section"]}. Parse a list of references from it:
            {snippit}
            """
        )
        print(prompt)
        return prompt

    def prepare_references(self):
        for subsection in self.statute.walk_subsections():
            snippit_text = subsection["text"]
            if snippit_text:
                prompt = self.generate_prompt(snippit_text)
                chat_stream = OllamaChatStream(
                    prompt=prompt,
                    model=self.model,
                )
                json = extract_json(chat_stream)[-1]

                subsection["references"] = json

            else:
                subsection["references"] = []
