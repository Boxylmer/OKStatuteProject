import requests


def generate(text, model="gemma3:12b-it-qat", num_ctx=None, top_k=None, top_p=None, temperature=None, seed=42):
    # https://github.com/ollama/ollama/blob/main/docs/modelfile.md#valid-parameters-and-values
    options = {}
    if num_ctx:
        options["num_ctx"] = num_ctx
    if top_k:
        options["top_k"] = top_k
    if top_p:
        options["top_p"] = top_p
    if temperature:
        options["temperature"] = temperature
    if seed:
        options["seed"] = seed

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model,
            "prompt": text,
            "stream": False,
            "options": options,
        },
    )
    response.raise_for_status()
    data = response.json()
    return data
