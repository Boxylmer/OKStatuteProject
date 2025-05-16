# import requests
import ollama


def generate_stream(instruction, prompt, model="adrienbrault/saul-instruct-v1:Q4_K_M", num_ctx=None, top_k=None, top_p=None, temperature=None, seed=42, verbose=False):
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

    # Use the stream=True generator to yield responses as they come in
    stream = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": text}],
        options=options,
        stream=True,
    )

    # Yield each streamed chunk of content
    for chunk in stream:
        text = chunk['message']['content'] 
        if verbose:
            print(text, end='')
        yield text
    
    print()

# def generate(text, model="gemma3:12b-it-qat", num_ctx=None, top_k=None, top_p=None, temperature=None, seed=42):
#     # https://github.com/ollama/ollama/blob/main/docs/modelfile.md#valid-parameters-and-values
#     options = {}
#     if num_ctx:
#         options["num_ctx"] = num_ctx
#     if top_k:
#         options["top_k"] = top_k
#     if top_p:
#         options["top_p"] = top_p
#     if temperature:
#         options["temperature"] = temperature
#     if seed:
#         options["seed"] = seed

#     response = requests.post(
#         "http://localhost:11434/api/generate",
#         json={
#             "model": model,
#             "prompt": text,
#             "stream": False,
#             "options": options,
#         },
#     )
#     response.raise_for_status()
#     data = response.json()
#     return data
