from pathlib import Path
import requests # type: ignore
import zipfile
import tarfile

from llama_cpp import Llama

DATA_PATH = Path("data")


def download_model(model_name: str):
    """
    Downloads and saves the GGUF model to a specified directory.
    
    Args:
    model_name (str): Name for the model, used to generate the download URL.
    
    Returns:
    Path: The path to the downloaded model directory.
    """
    # Define the URL and directory based on the model name
    model_url = f"https://huggingface.co/{model_name}/resolve/main/{model_name}.gguf"
    save_dir = DATA_PATH / 'models' / model_name
    save_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if model already exists
    if save_dir.exists():
        print(f"Model {model_name} already exists at {save_dir}")
        return save_dir
    
    # Start the download
    print(f"Downloading model {model_name} from {model_url} to {save_dir}...")
    try:
        response = requests.get(model_url, stream=True)
        response.raise_for_status()
        
        # Save the model file
        model_file = save_dir / f"{model_name}.gguf"
        with open(model_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Model downloaded successfully to {model_file}")
        
        return save_dir
    except requests.exceptions.RequestException as e:
        print(f"Failed to download model: {e}")
        return None
    
def unzip_or_extract(model_path: Path):
    """
    Checks if the model is a .zip or .tar.gz file and extracts it.
    
    Args:
    model_path (Path): Path to the model file.
    """
    if model_path.suffix == '.zip':
        with zipfile.ZipFile(model_path, 'r') as zip_ref:
            zip_ref.extractall(model_path.parent)
        print(f"Model unzipped to {model_path.parent}")
    elif model_path.suffix in ['.tar', '.tar.gz', '.tgz']:
        with tarfile.open(model_path, 'r:*') as tar_ref:
            tar_ref.extractall(model_path.parent)
        print(f"Model extracted to {model_path.parent}")
    else:
        print(f"Model is already in GGUF format: {model_path}")

def get_callable_model(model_name: str):
    """
    Downloads the GGUF model, extracts it if needed, and returns a callable model.
    
    Args:
    model_name (str): Model name used for the file.
    
    Returns:
    callable: A callable function that uses the model for inference.
    """
    # Download the model and get the path
    model_path = download_model(model_name)
    
    if model_path:
        model_file = model_path / f"{model_name}.gguf"
        unzip_or_extract(model_file)
        
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