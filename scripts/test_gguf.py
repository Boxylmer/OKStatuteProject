from rag.utils import download_gguf_model, load_langchain_llm
from llama_cpp import Llama

# Download and load Mixtral for LangChain
gguf_path = download_gguf_model(
    repo_id="TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
    filename="mistral-7b-instruct-v0.2.Q4_K_M.gguf",
)
llm = load_langchain_llm(gguf_path, max_tokens=10)

# Try it
prompt = "### Instruction:\nSummarize the following legal text:\n...\n### Response:"
response = llm(prompt)
print(response)



def get_callable_model(model_url: str, save_dir: str = 'models', model_name: str = 'mistral-7b-instruct'):
    """
    Downloads the GGUF model, extracts it if needed, and returns a callable model.
    
    Args:
    model_url (str): URL to the model file.
    save_dir (str): Directory to save the model to.
    model_name (str): Model name used for the file.
    
    Returns:
    callable: A callable function that uses the model for inference.
    """
    # Download and prepare the model
    model_file = download_and_prepare_model(model_url, save_dir, model_name)
    
    if model_file:
        # Initialize the Llama model
        model = Llama(model_path=str(model_file))

        # Return a callable model
        def model_call(prompt: str):
            result = model(prompt)
            return result["text"]

        return model_call
    else:
        print("Failed to load the model.")
        return None