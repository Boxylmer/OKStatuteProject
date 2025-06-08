from statute.statute import Statute

from nlp.ollama import OllamaChatStream

IRRELEVANT_TOKEN = "[n/a]"

SYSTEM = f"""
You are a paralegal. Your task is to extract relevant information from legal statutes you are presented with respect to some context information.
As a paralegal, you must be dry and logical. You must take care not to add in new infromation or speculate when making logical conclusions during extraction.
Extraction should be relevant details without further elaboration. You are essentially reporting facts and details from the statute. 

Some statutes are not relevant to the context, if you run into a statute that you believe isn't relevant, respond ONLY with "{IRRELEVANT_TOKEN}"
"""

SYSTEM_NO_CONTEXT = """
You are a paralegal. Your task is to extract relevant information from legal statutes you are presented.
As a paralegal, you must be dry and logical. You must take care not to add in new infromation or speculate when making logical conclusions during extraction.
Extraction should be relevant details without further elaboration. You are essentially reporting facts and details from the statute. 
"""


class StatuteSummarizer:
    def __init__(
        self, model="adrienbrault/saul-instruct-v1:Q4_K_M", llm_context_length=16384
    ):
        self.model = model
        self.context_length = llm_context_length

    def summarize(
        self,
        statute: Statute,
        context: str | None = None,
        verbose=False,  # optional: timeout_seconds ? TODO
    ) -> str:
        """Runs the LLM to extract penalties from a statute."""
        statute_text = f"STATUTE: [{statute.formatted_text()}]"
        if context:
            prompt = (
                f"Context: [{context}]\n\n"
                f"Statute: [{statute_text}]\n\n"
                "Based on the statute and context above, extract relevant details:"
            )
            system = SYSTEM

        else:
            prompt = (
                f"Statute: [{statute_text}]\n\n"
                "Summarize the staute and its information:"
            )
            system = SYSTEM_NO_CONTEXT

        response_stream = OllamaChatStream(
            prompt=prompt,
            system=system,
            model=self.model,
            num_ctx=self.context_length,
            top_k=1,
            top_p=1,
            temperature=0,
            verbose=verbose,
        )

        response = "".join(response_stream)
        print(response)

        if (
            response_stream.prompt_eval_count + response_stream.eval_count
            > self.context_length
        ):
            raise RuntimeError(
                f"LLM query exceeded allowed context length ({self.context_length}). prompt: {response_stream.prompt_eval_count}, response: {response_stream.eval_count}"
            )
        return response
