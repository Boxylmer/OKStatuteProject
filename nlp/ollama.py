import ollama


class OllamaChatStream:
    """
    Class wrapper for streaming a response from an Ollama model using the chat API.

    This class provides a flexible interface compatible with both
    chat-optimized models (e.g., Gemma, Mistral-chat) and instruct-tuned models
    (e.g., saul-instruct), using the `ollama.chat()` method to abstract message formatting.

    Args:
        prompt (str): The main user query or task to be executed.
        instruction (str, optional): An optional pre-context instruction. This is added
            as a user message *before* the main prompt. Useful for extra guidance or multi-part context.
        system (str, optional): A system-level instruction used to define assistant behavior,
            tone, or domain knowledge. Supported directly in chat models; for instruct models,
            it becomes part of the flattened prompt.
        primer (str, optional): Optional starter text for the assistant's reply. This is included
            as the first assistant message and can help guide the model's output format
            (e.g., "Here's the summary:").
        model (str): Name of the Ollama model to use.
        num_ctx (int, optional): Maximum context window to use.
        top_k (int, optional): Number of top logits to sample from.
        top_p (float, optional): Nucleus sampling threshold.
        temperature (float, optional): Sampling temperature for randomness.
        seed (int, optional): Random seed for reproducibility.
        verbose (bool): If True, prints streaming chunks and final output.
        validate_output: Check that the output stayed within the given context length. Raise an error if output did not.

    Notes:
        - `ollama.chat()` automatically adapts message formatting based on the model type.
        - For chat models, `system`, `instruction`, and `primer` are interpreted with their intended roles.
        - For instruct models, all messages are merged into a single prompt internally,
          but the logical structure (e.g., using `system` and `instruction`) still make their way through.
    """

    def __init__(
        self,
        prompt: str,
        model: str,
        instruction=None,
        system=None,
        primer=None,
        num_ctx: str | None = None,
        top_k=None,
        top_p=None,
        temperature=None,
        seed=42,
        verbose=False,
        validate_output=True,
    ):
        self.verbose = verbose
        self.final_chunk = None
        self.stream = None
        self.done = False
        self.validate_output = validate_output
        self.context_length = num_ctx

        options = {}
        if num_ctx is not None:
            options["num_ctx"] = num_ctx
        if top_k is not None:
            options["top_k"] = top_k
        if top_p is not None:
            options["top_p"] = top_p
        if temperature is not None:
            options["temperature"] = temperature
        if seed is not None:
            options["seed"] = seed

        messages = []

        if system:
            messages.append({"role": "system", "content": system})

        if instruction:
            messages.append({"role": "user", "content": instruction})

        messages.append({"role": "user", "content": prompt})

        if primer:
            messages.append({"role": "assistant", "content": primer})

        self.stream = ollama.chat(  # type: ignore
            model=model,
            messages=messages,
            options=options,
            stream=True,
        )

    def __iter__(self):
        return self

    def __next__(self):
        if self.done:
            raise StopIteration

        try:
            chunk = next(self.stream)
            self.final_chunk = chunk
            text = chunk["message"]["content"]
            if self.verbose:
                print(text, end="", flush=True)
            return text

        except StopIteration:
            self.done = True
            if self.verbose:
                print()

            if self.validate_output:
                if self.prompt_eval_count + self.eval_count > self.context_length:
                    raise RuntimeError(
                        f"LLM query exceeded allowed context length ({self.context_length}).\n"
                        f"prompt: {self.prompt_eval_count}, response: {self.eval_count}"
                    )
            raise

    def is_done(self):
        return self.done

    @property
    def total_duration(self):
        return self.final_chunk.get("total_duration") if self.final_chunk else None

    @property
    def load_duration(self):
        return self.final_chunk.get("load_duration") if self.final_chunk else None

    @property
    def prompt_eval_count(self) -> int | None:
        return self.final_chunk.get("prompt_eval_count") if self.final_chunk else None

    @property
    def prompt_eval_duration(self) -> float | None:
        return (
            self.final_chunk.get("prompt_eval_duration") if self.final_chunk else None
        )

    @property
    def eval_count(self) -> int | None:
        return self.final_chunk.get("eval_count") if self.final_chunk else None

    @property
    def eval_duration(self) -> float | None:
        return self.final_chunk.get("eval_duration") if self.final_chunk else None

    @property
    def total_eval_count(self) -> int | None:
        if self.eval_count and self.prompt_eval_count:
            return self.eval_count + self.prompt_eval_count
        return None
