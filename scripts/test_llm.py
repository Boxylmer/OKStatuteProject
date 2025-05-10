from rag.utils import download_quantized_model, load_transformers_pipeline

# Use a Transformers 4-bit compatible model (AWQ or original weights)
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
model_path = download_quantized_model("TheBloke/Mistral-7B-Instruct-v0.2-GPTQ")  # or TheBloke/*-AWQ
tokenizer = AutoTokenizer.from_pretrained(model_path, use_fast=True)
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    device_map="auto",
    trust_remote_code=True
)
llm_pipeline = load_transformers_pipeline(model_path, use_gpu=True)

prompt = (
    "### Instruction:\n"
    "You are a paralegal. The goal is to extract statute information from the INPUT text in the format of [statute description, range of punishments, range of fines, exceptions, resitution / misc punishments, notes, felony or misdameanor]:\n"
    "### Example Output: [Driving while intoxicated, 30 days to 2 years in prison, $25-$1000, minors do not apply, N/a, misdameanor]\n"
    "Note that you are being fed the entire statute book sequentially, thus some sections will have zero relevant rows, and some could have multiple."
    "### INPUT: \n"
    "The right to control the disposition of the remains of a deceased person, the location, manner and conditions of disposition, and arrangements for funeral goods and services vests in the following order, provided the person is eighteen (18) years of age or older and of sound mind: 1. The decedent, provided the decedent has entered into a pre-need funeral services contract or executed a written document that meets the requirements of the State of Oklahoma;"
    "### Rows:\n"
)

response = llm_pipeline(prompt, max_new_tokens=512)
print(response[0]["generated_text"])