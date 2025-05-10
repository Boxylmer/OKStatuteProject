from rag.utils import get_callable_model
model_url = 'https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/blob/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf'
download_and_prepare_model(model_url)


call_model = get_callable_model(model_name='mistral-7b-instruct-v0.2')

prompt = "### Instruction:\nSummarize the following legal text:\n...\n### Response:"
response = call_model(prompt)
print(response)