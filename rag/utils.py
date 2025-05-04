import os
from pathlib import Path
from sentence_transformers import SentenceTransformer


def download_embedding_model(
    model_name: str = "hkunlp/instructor-base",
    model_dir: str | Path = Path("data") / "embedding_models",
    verbose=False
):
    model_path = os.path.join(model_dir, model_name.replace("/", "_"))
    if not os.path.exists(model_path):
        if verbose:
            print(f"Downloading model {model_name} to {model_path}...")
        model = SentenceTransformer(model_name)
        model.save(model_path)
    else:
        if verbose:
            print(f"Model {model_name} already present at {model_path}")
    return model_path
